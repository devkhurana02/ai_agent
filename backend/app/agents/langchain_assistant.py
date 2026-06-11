"""Assistant agent with LangChain.

The main conversational agent that can be extended with custom tools.
"""

import logging
from typing import Any, TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph

from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
from app.agents.tools import get_current_datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentContext(TypedDict, total=False):
    """Runtime context for the agent.

    Passed via context parameter to agent.invoke()/stream().
    """

    user_id: str | None
    user_name: str | None
    metadata: dict[str, Any]


@tool
def current_datetime() -> dict[str, str]:
    """Get the current date and time.

    Use this tool when you need to know the current date or time.
    """
    return get_current_datetime()


class LangChainAssistant:
    """Assistant agent wrapper for conversational AI using LangChain.

    Encapsulates agent creation and execution with tool support.
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        thinking_effort: str | None = None,
    ):
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = temperature or settings.AI_TEMPERATURE
        # Extended-thinking effort for reasoning-capable models. ``None`` keeps
        # the model in plain mode; "low"/"medium"/"high" enables provider-
        # specific reasoning (Claude extended thinking, OpenAI o-series, etc).
        self.thinking_effort = (
            thinking_effort
            if thinking_effort is not None
            else (settings.AI_THINKING_EFFORT if settings.AI_THINKING_ENABLED else None)
        )
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._agent: CompiledStateGraph | None = None
        self._tools = [current_datetime]

    def _create_agent(self) -> CompiledStateGraph:
        """Create and configure the LangChain agent."""
        # OpenAI: ``reasoning`` is honored only by the Responses API.
        openai_kwargs: dict[str, Any] = {}
        if self.thinking_effort:
            openai_kwargs["reasoning"] = {
                "effort": self.thinking_effort,
                "summary": "auto",
            }
            openai_kwargs["use_responses_api"] = True
            openai_kwargs["output_version"] = "responses/v1"
        model = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
            **openai_kwargs,
        )

        return create_agent(
            model=model,
            tools=self._tools,
            system_prompt=self.system_prompt,
            context_schema=AgentContext,
            middleware=[
                ModelRetryMiddleware(max_retries=2),
                ToolRetryMiddleware(max_retries=1),
                ToolCallLimitMiddleware(run_limit=15),
            ],
        )

    @property
    def agent(self) -> CompiledStateGraph:
        """Get or create the agent instance."""
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    @staticmethod
    def _convert_history(
        history: list[dict[str, str]] | None,
    ) -> list[HumanMessage | AIMessage | SystemMessage]:
        """Convert conversation history to LangChain message format."""
        messages: list[HumanMessage | AIMessage | SystemMessage] = []

        for msg in history or []:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                messages.append(SystemMessage(content=msg["content"]))

        return messages

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
    ) -> tuple[str, list[Any], AgentContext]:
        """Run agent and return the output along with tool call events.

        Args:
            user_input: User's message.
            history: Conversation history as list of {"role": "...", "content": "..."}.
            context: Optional runtime context with user info.

        Returns:
            Tuple of (output_text, tool_events, context).
        """
        messages = self._convert_history(history)
        messages.append(HumanMessage(content=user_input))

        agent_context: AgentContext = context if context is not None else {}

        logger.info(f"Running agent with user input: {user_input[:100]}...")
        result = await self.agent.ainvoke(
            {"messages": messages},
            config={"configurable": agent_context} if agent_context else None,
        )

        # Extract the final response
        output = ""
        tool_events: list[Any] = []

        for message in result.get("messages", []):
            if hasattr(message, "content") and isinstance(message, AIMessage):
                output = message.content
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_events.extend(message.tool_calls)

        logger.info(f"Agent run complete. Output length: {len(output)} chars")

        return output, tool_events, agent_context

    async def stream(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
    ):
        """Stream agent execution with token-level streaming.

        Args:
            user_input: User's message.
            history: Conversation history.
            context: Optional runtime context.

        Yields:
            Tuples of (stream_mode, data) for streaming responses.
            - stream_mode="messages": (token, metadata) for LLM tokens
            - stream_mode="updates": state updates after each step
        """
        messages = self._convert_history(history)
        messages.append(HumanMessage(content=user_input))

        agent_context: AgentContext = context if context is not None else {}
        async for event in self.agent.astream(
            {"messages": messages},
            stream_mode=["messages", "updates"],
            config={"configurable": agent_context} if agent_context else None,
        ):
            yield event


def get_agent(
    model_name: str | None = None,
    thinking_effort: str | None = None,
) -> LangChainAssistant:
    """Factory function to create a LangChainAssistant.

    Args:
        model_name: Override the default AI model.
        thinking_effort: Extended-thinking effort ("low"/"medium"/"high") or
            ``None`` to disable. Wired to ``thinking={...}`` for Anthropic and
            ``reasoning={...}`` for OpenAI Responses-API models.

    Returns:
        Configured LangChainAssistant instance.
    """
    return LangChainAssistant(model_name=model_name, thinking_effort=thinking_effort)


async def run_agent(
    user_input: str,
    history: list[dict[str, str]],
    context: AgentContext | None = None,
) -> tuple[str, list[Any], AgentContext]:
    """Run agent and return the output along with tool call events.

    This is a convenience function for backwards compatibility.

    Args:
        user_input: User's message.
        history: Conversation history.
        context: Optional runtime context.

    Returns:
        Tuple of (output_text, tool_events, context).
    """
    agent = get_agent()
    return await agent.run(user_input, history, context)
