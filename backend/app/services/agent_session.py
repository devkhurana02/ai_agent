"""Per-connection AI agent session (LangChain)."""

import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from langchain.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.messages.ai import add_usage

from app.agents.langchain_assistant import AgentContext, get_agent
from app.db.models.user import User
from app.services.agent import (
    build_message_history,
    persist_assistant_turn,
    persist_user_turn,
    send_event,
)

logger = logging.getLogger(__name__)


class AgentSession:
    """One WebSocket session with the LangChain agent."""

    def __init__(
        self,
        websocket: WebSocket,
        user: User,
    ) -> None:
        self.websocket = websocket
        self.user = user
        self.conversation_history: list[dict[str, str]] = []
        self.context: AgentContext = {}
        self.context["user_id"] = str(user.id) if user else None
        self.context["user_name"] = user.email if user else None
        self.current_conversation_id: str | None = None

    async def process_message(self, data: dict[str, Any]) -> None:
        """Process one user turn: persist input, run the agent, stream events, persist output."""
        user_message = data.get("message", "")
        file_ids = data.get("file_ids", [])

        if not user_message and not file_ids:
            await send_event(self.websocket, "error", {"message": "Empty message"})
            return
        self.current_conversation_id, newly_created, organization_id = await persist_user_turn(
            self.user,
            user_message,
            file_ids,
            requested_conversation_id=data.get("conversation_id"),
            current_conversation_id=self.current_conversation_id,
        )
        if newly_created and self.current_conversation_id:
            await send_event(
                self.websocket,
                "conversation_created",
                {"conversation_id": self.current_conversation_id},
            )

        await send_event(self.websocket, "user_prompt", {"content": user_message})

        try:
            assistant = get_agent(
                model_name=data.get("model"),
                thinking_effort=data.get("thinking_effort"),
            )
            model_history = build_message_history(self.conversation_history)
            model_history.append(HumanMessage(content=user_message))
            collected_tool_calls: list[dict[str, Any]] = []
            final_output = await self._stream_agent_response(
                assistant, model_history, collected_tool_calls
            )

            # Update in-memory history only after the agent produced output
            if final_output:
                self.conversation_history.append({"role": "user", "content": user_message})
                self.conversation_history.append({"role": "assistant", "content": final_output})
            assistant_msg_id: str | None = None
            if self.current_conversation_id and final_output:
                assistant_msg_id = await persist_assistant_turn(
                    self.current_conversation_id,
                    final_output,
                    getattr(assistant, "model_name", None),
                    collected_tool_calls,
                )

            if assistant_msg_id:
                await send_event(
                    self.websocket,
                    "message_saved",
                    {
                        "message_id": assistant_msg_id,
                        "conversation_id": self.current_conversation_id,
                    },
                )

            await send_event(
                self.websocket,
                "complete",
                {"conversation_id": self.current_conversation_id},
            )
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.exception(f"Error processing agent request: {e}")
            await send_event(self.websocket, "error", {"message": str(e)})

    async def _stream_agent_response(
        self,
        assistant: Any,
        model_history: list[Any],
        collected_tool_calls: list[dict[str, Any]],
    ) -> str:
        """Run ``assistant.agent.astream`` and forward all events; return accumulated text."""
        final_output = ""
        seen_tool_call_ids: set[str] = set()
        pending: dict[str, dict[str, Any]] = {}
        # Sum usage_metadata across the turn's model calls. We add only the
        # usage dicts (via add_usage), never whole chunks — merging full
        # AIMessageChunks via `+` crashes on scalar additional_kwargs like the
        # OpenAI Responses API's float ``created_at``.
        self._last_usage_metadata = None
        # Per-turn flag: did we already stream reasoning from token chunks?
        # If not, _stream_update_event falls back to the final message's
        # reasoning so thinking is shown for providers that don't stream it.
        self._thinking_streamed = False

        await send_event(self.websocket, "model_request_start", {})

        async for stream_mode, data in assistant.agent.astream(
            {"messages": model_history},
            stream_mode=["messages", "updates"],
            config={"configurable": self.context} if self.context else None,
        ):
            if stream_mode == "messages":
                token, _metadata = data
                if isinstance(token, AIMessageChunk):
                    if token.usage_metadata:
                        self._last_usage_metadata = (
                            token.usage_metadata
                            if self._last_usage_metadata is None
                            else add_usage(self._last_usage_metadata, token.usage_metadata)
                        )
                    final_output += await self._stream_message_chunk(token)
            elif stream_mode == "updates":
                await self._stream_update_event(
                    data, seen_tool_call_ids, pending, collected_tool_calls
                )

        await send_event(self.websocket, "final_result", {"output": final_output})
        return final_output

    @staticmethod
    def _extract_reasoning(message: Any) -> str:
        """Pull reasoning/thinking text from a LangChain message or chunk.

        Covers three shapes:
          * Anthropic extended thinking — ``{"type":"thinking","thinking":"..."}``
          * OpenAI Responses API — ``{"type":"reasoning","summary":[{"type":"summary_text","text":"..."}]}``
          * Legacy providers — ``additional_kwargs.reasoning_content`` (string)
        """
        out = ""
        content = getattr(message, "content", None)
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "thinking":
                    out += block.get("thinking", "") or ""
                elif btype == "reasoning":
                    for summary in block.get("summary", []) or []:
                        if isinstance(summary, dict) and summary.get("type") == "summary_text":
                            out += summary.get("text", "") or ""
        legacy = (getattr(message, "additional_kwargs", None) or {}).get("reasoning_content")
        if isinstance(legacy, str):
            out += legacy
        return out

    async def _stream_message_chunk(self, token: AIMessageChunk) -> str:
        """Emit text + reasoning deltas from a streaming chunk.

        Tool calls are intentionally NOT emitted here. Streamed
        ``tool_call_chunks`` carry only partial JSON-string argument
        fragments, not a usable args dict — emitting from here produced
        ``tool_call`` events with empty ``args`` (and, because they were
        deduped against the same id set, suppressed the complete event).
        The canonical tool call, with full args, is emitted from the
        ``updates`` stream in ``_stream_update_event``.
        """
        text_content = ""
        if token.content:
            if isinstance(token.content, str):
                text_content = token.content
            elif isinstance(token.content, list):
                for block in token.content:
                    if isinstance(block, str):
                        text_content += block
                    elif isinstance(block, dict) and block.get("type") == "text":
                        text_content += block.get("text", "")
            if text_content:
                await send_event(self.websocket, "text_delta", {"content": text_content})

        reasoning_content = self._extract_reasoning(token)
        if reasoning_content:
            self._thinking_streamed = True
            await send_event(self.websocket, "thinking_delta", {"content": reasoning_content})
        return text_content

    async def _stream_update_event(
        self,
        update_data: dict[str, Any],
        seen_tool_call_ids: set[str],
        pending: dict[str, dict[str, Any]],
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Process ``updates`` stream events — the source of truth for tools.

        Tool calls here carry the complete name + parsed ``args`` from
        ``AIMessage.tool_calls`` (unlike the partial streamed chunks). Also
        emits a reasoning fallback for providers that attach the chain of
        thought to the final message instead of streaming it.
        """
        for node_name, update in update_data.items():
            if node_name == "tools":
                for msg in update.get("messages", []):
                    if isinstance(msg, ToolMessage):
                        tc = pending.get(msg.tool_call_id)
                        if tc is not None:
                            tc["result"] = str(msg.content)
                        await send_event(
                            self.websocket,
                            "tool_result",
                            {"tool_call_id": msg.tool_call_id, "content": msg.content},
                        )
            elif node_name == "model":
                for msg in update.get("messages", []):
                    if not isinstance(msg, AIMessage):
                        continue
                    if not self._thinking_streamed:
                        reasoning = self._extract_reasoning(msg)
                        if reasoning:
                            self._thinking_streamed = True
                            await send_event(
                                self.websocket,
                                "thinking_delta",
                                {"content": reasoning},
                            )
                    for tc_in in msg.tool_calls or []:
                        tc_id = tc_in.get("id", "")
                        if not tc_id:
                            continue
                        tc = {
                            "tool_call_id": tc_id,
                            "tool_name": tc_in.get("name", ""),
                            "args": tc_in.get("args", {}),
                        }
                        pending[tc_id] = tc
                        collected_tool_calls.append(tc)
                        if tc_id not in seen_tool_call_ids:
                            seen_tool_call_ids.add(tc_id)
                            await send_event(self.websocket, "tool_call", tc)
