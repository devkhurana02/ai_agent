<p align="center">
  <img src="https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/chat_demo.gif" alt="Live chat — web search, tool calls, and chart generation" width="100%">
</p>

<h1 align="center">Full-Stack AI Agent Template</h1>

<p align="center">
  <i>Production-ready FastAPI + Next.js project generator with AI agents, RAG, and 20+ enterprise integrations.</i>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-demo">Demo</a> •
  <a href="https://vstorm-co.github.io/full-stack-ai-agent-template/">Documentation</a> •
  <a href="https://oss.vstorm.co/projects/full-stack-ai-agent-template/configurator/">Configurator</a>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/LICENSE"><img src="https://img.shields.io/github/license/vstorm-co/full-stack-ai-agent-template?color=blue" alt="License"></a>
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage">
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/actions/workflows/ci.yml"><img src="https://github.com/vstorm-co/full-stack-ai-agent-template/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/SECURITY.md"><img src="https://img.shields.io/badge/security-policy-blueviolet?logo=shieldsdotio&logoColor=white" alt="Security Policy"></a>
</p>

<p align="center">
  <b>🤖 6 AI Agent Frameworks</b> <i>(PydanticAI, PydanticDeep, LangChain, LangGraph, CrewAI, DeepAgents)</i>
  <br>
  <b>📄 RAG Pipeline</b> <i>(Milvus, Qdrant, pgvector, ChromaDB)</i>
  <br>
  <b>⚡ FastAPI + Next.js 15</b> <i>(WebSocket streaming, real-time chat UI)</i>
  <br>
  <b>🔗 Conversation Sharing</b> <i>(direct sharing, public links, admin browser)</i>
  <br>
  <b>🔒 Enterprise-Ready</b> <i>(JWT, OAuth, admin panel, Celery, Docker, K8s)</i>
</p>

<details>
<summary><b>Table of Contents</b></summary>

- [Quick Start](#-quick-start)
- [Demo](#-demo)
- [Screenshots](#-screenshots)
- [Why This Template](#-why-this-template)
- [Features](#-features)
- [Architecture](#-architecture)
- [AI Agent](#-ai-agent)
- [RAG](#-rag-retrieval-augmented-generation)
- [Observability](#-observability)
- [Django-style CLI](#-django-style-cli)
- [Generated Project Structure](#-generated-project-structure)
- [Configuration Options](#-configuration-options)
- [Comparison](#-comparison)
- [FAQ](#-faq)
- [Documentation](#-documentation)

</details>

---

## 🚀 Quick Start

> [!TIP]
> **Prefer a visual configurator?** Use the [Web Configurator](https://oss.vstorm.co/projects/full-stack-ai-agent-template/configurator/) to configure your project in the browser and download a ZIP — no CLI installation needed.

### Installation

```bash
# pip
pip install fastapi-fullstack

# uv (recommended)
uv tool install fastapi-fullstack

# pipx
pipx install fastapi-fullstack
```

### Create Your Project

```bash
# Interactive wizard (recommended — runs by default)
fastapi-fullstack

# Quick mode with options
fastapi-fullstack create my_ai_app \
  --database postgresql \
  --frontend nextjs

# Use presets for common setups
fastapi-fullstack create my_ai_app --preset production   # Full production setup
fastapi-fullstack create my_ai_app --preset ai-agent     # AI agent with streaming

# Minimal project (no extras)
fastapi-fullstack create my_ai_app --minimal
```

### Start Development

#### First time on a fresh clone

```bash
cd my_ai_app
make bootstrap       # = make dev + make seed
```

That's it — backend, database, Redis, vector store (if RAG), Celery (if selected) come up, migrations are applied, and a default admin is seeded.

#### Day-to-day

```bash
make dev             # idempotent: build + up + migrate. Re-run anytime.
```

`make dev` skips admin seeding (that's a one-shot in `make seed`) so it stays cheap to run after every code/config change.

**Behind the scenes (`make dev`):**

1. Builds the backend Docker image (cached after first run)
2. Starts services via `docker-compose.dev.yml` (hot-reload bind mounts)
3. Polls Postgres until ready (`pg_isready` — no fixed sleeps)
4. Applies pending Alembic migrations (no-op if already at head)

**Then access:**

| | URL | |
|---|---|---|
| Backend API | <http://localhost:8000> | |
| Docs | <http://localhost:8000/docs> | OpenAPI / Swagger |
| Admin | <http://localhost:8000/admin> | `admin@example.com` / `admin123` (after `make seed`) |
| Frontend | <http://localhost:3000> | `make dev-frontend` (Docker) or `cd frontend && bun install && bun dev` (local) |

### Day-to-day commands

```bash
make dev           # bootstrap or restart (no admin re-seed)
make seed          # one-shot admin creation (no-op if admin exists)
make dev-down      # stop everything
make dev-logs      # tail container logs
make dev-rebuild   # force-rebuild backend image (after pyproject.toml changes)
make dev-frontend  # start the Next.js container
```

### Environments

| `make` target | Compose file | When to use |
|---|---|---|
| `make dev` | `docker-compose.dev.yml` | Local development with hot-reload + bind-mounted source. |
| `make stage` | `docker-compose.yml` | Production-like build (no bind mounts) running on localhost. Sanity-check before deploy. |
| `make prod` | `docker-compose.prod.yml` | Production. Requires `backend/.env` (copy from `backend/.env.example`, fill real secrets) + external Nginx using `nginx/nginx.conf`. |

Each env has matching `-down`, `-logs`, `-rebuild` siblings.

> [!NOTE]
> **Windows users:** `make` requires GNU Make. Install via [Chocolatey](https://chocolatey.org/) (`choco install make`) or use **WSL2 / Git Bash**. The Docker workflow is identical across macOS, Linux, and WSL2.

<details>
<summary><b>Local backend (no Docker, for IDE breakpoints)</b></summary>

If you want to run the backend on the host while the database stays in Docker:

```bash
cd my_ai_app
make install                                                # uv sync + pre-commit hooks

# Start only infrastructure containers
docker compose -f docker-compose.dev.yml up -d db redis    # add 'milvus etcd minio' if RAG

make db-upgrade                                             # apply migrations
make create-admin                                           # interactive
make run                                                    # uvicorn --reload
```

</details>

<details>
<summary><b>Production deploy</b></summary>

```bash
# On your server
git clone <your-repo>
cd my_ai_app

cp backend/.env.example backend/.env            # fill in real secrets
# Configure your nginx host using nginx/nginx.conf as reference

make prod                                       # builds + starts + migrates
make prod-logs                                  # tail logs
```

For frontend deployment to **Vercel**:

```bash
cd frontend && npx vercel --prod
```

In the Vercel dashboard set `BACKEND_URL`, `BACKEND_WS_URL`, `NEXT_PUBLIC_AUTH_ENABLED=true`.

</details>

### Using the Project CLI

Each generated project has a CLI named after your `project_slug`. For example, if you created `my_ai_app`:

```bash
cd backend

# The CLI command is: uv run <project_slug> <command>
uv run my_ai_app server run --reload     # Start dev server
uv run my_ai_app db migrate -m "message" # Create migration
uv run my_ai_app db upgrade              # Apply migrations
uv run my_ai_app user create-admin       # Create admin user
```

Use `make help` to see all available Makefile shortcuts.

---

## 🎬 Demo

**CLI generator:**

<p align="center">
  <img src="https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/app_start.gif" alt="FastAPI Fullstack Generator Demo">
</p>

**File upload & RAG ingestion:**

<p align="center">
  <img src="https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/rag_demo.gif" alt="File upload &amp; RAG ingestion" width="100%">
</p>

---

## 📸 Screenshots

### Marketing Site

**Landing Page** — Full-page marketing site with hero, features breakdown, testimonials, pricing preview, and FAQ. Generated with the `enable_marketing_site` option.

![Landing Page](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/landing_page.png)

**Pricing** — Three-tier pricing page (Starter / Pro / Business) with monthly/annual toggle. Pulls live plan data from Stripe when connected; shows template plans otherwise.

![Pricing](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/pricing.png)

**Blog** — Engineering blog included out of the box. Posts are MDX files in the repo — no CMS needed. Supports tags, featured posts, and author bylines.

![Blog](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/blog.png)

**Blog Post** — Individual post view with author card, reading time, and tag badges. Content is plain MDX — edit files and redeploy.

![Blog Post](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/blog_post.png)

### Auth

**Login** — Split-screen login with Google OAuth and email/password. Left panel shows a product pitch with a social proof quote. HTTP-only cookie session on submit.

![Login](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/login.png)

**Register** — Same split-screen layout as login. Google sign-up and email/password form with confirm-password field and terms acceptance.

![Register](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/register.png)

### Dashboard

**Dashboard (light mode)** — Workspace overview showing conversation count, knowledge base vector count, recent activity feed, agent tool call stats, active sessions, and team info. Onboarding banner guides new users through setup in under 2 minutes.

![Dashboard Light](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/dashboard_light.png)

**Dashboard (dark mode)** — Same dashboard in dark theme. Theme is saved per-device and can be overridden per-workspace in appearance settings.

![Dashboard Dark](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/dashboard_dark.png)

### Teams & Organizations

**Workspaces** — List of all organizations the user belongs to. Shows plan tier and role for each. Users can switch active workspace or create a new organization.

![Organizations](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/organizations.png)

**Team Management** — Organization detail page with workspace profile (name + avatar), member list with roles, and an "Invite teammate" button. Owners and admins can adjust roles inline.

![Organization Details](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/organization_details.png)

### Knowledge Bases

**Knowledge Bases** — List of RAG knowledge bases scoped to the current workspace. Each base shows its collection slug. Users can create new bases, toggle which ones are active in chat, and upload documents through the UI.

![Knowledge Bases](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/knowledge_bases.png)

### Billing

**Billing** — Workspace billing dashboard showing current plan, storage usage (chat attachments + indexed RAG documents), quick links to usage breakdown, invoices, payment methods, and subscription management. "Manage in Stripe" opens the Stripe customer portal.

![Billing](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/billing.png)

### Profile & Settings

**Profile** — Personal info tab: avatar upload, display name, email, and active session list with per-device revoke buttons. Visibility note explains which fields are shown to teammates.

![Profile](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/profile.png)

**Account & Security** — Change password form with strength guidance, "Sign out everywhere" button, and danger zone for permanent account deletion.

![Account](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/profile_account.png)

**Slash Commands** — Customize the `/command` palette in chat. Toggle built-in commands (`/clear`, `/regen`, `/settings`, `/summarize`, `/explain`) and create custom shortcuts that send a stored prompt with a few keystrokes.

![Slash Commands](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/profile_commands.png)

**Appearance** — Theme switcher (light / dark / system) and brand color picker with four presets: Blue (Stripe/Vercel), Green (healthtech), Red (energetic), Orange (B2C), Violet (Anthropic-style). Brand color updates CSS variables across the entire workspace and is saved per-device.

![Appearance](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/profile_appearance.png)

**Notification Preferences** — Per-category notification controls with separate toggles for email and in-app delivery. Categories: Billing, Team activity, Security alerts, and Product updates. Preferences stored locally and synced to the backend via `/users/me/notifications`.

![Notifications](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/profile_notifications.png)

### Admin Panel

**Admin Overview** — Workspace-wide metrics (total users, active sessions last 24h, conversation count, MRR) plus a recent activity feed showing all conversations across all users. Requires the `admin` role.

![Admin Overview](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/admin_overview.png)

**User Management** — Full user list with search by email or name. Shows role, status, join date, and an "Inspect" action to impersonate or suspend any user. Pagination built in.

![Admin Users](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/admin_users.png)

**Conversation Browser** — Browse all conversations across the workspace. Filter by status and owner, sort by any column, open any conversation in a read-only view. Useful for support and quality review.

![Admin Conversations](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/admin_conversations.png)

**Message Quality & Ratings** — Aggregated like/dislike feedback on AI responses over the last 30 days. Shows approval rate, daily chart, and a filterable table of individual ratings with optional user comments. Export to CSV.

![Admin Ratings](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/admin_ratings.png)

**Stripe Events Log** — Webhook event browser for debugging Stripe billing flows. Lists all received events (type, customer, amount, status, timestamp) and lets admins manually replay any event via the backend `/admin/stripe-events/{id}/replay` endpoint.

![Stripe Events](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/admin_stripe_events.png)

**System Health** — Live readiness dashboard auto-refreshing every 30 seconds. Checks API, Database (PostgreSQL primary), Redis, Vector store, LLM provider, Background worker, and Stripe API. Shows uptime percentage per service.

![System Health](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new2/admin_system_health.png)

### Observability

**Logfire (PydanticAI)** — Full distributed tracing for PydanticAI agent runs, FastAPI requests, database queries, Redis, Celery tasks, and HTTPX calls — all in one timeline.

![Logfire](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/logfire.png)

**LangSmith (LangChain / LangGraph)** — Trace viewer for LangChain agent runs with step-by-step chain inspection, token usage, and feedback collection.

![LangSmith](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/langsmith.png)

### Messaging Channels

**Telegram Bot** — Multi-bot integration with both polling and webhook modes. Each bot gets its own session, supports group concurrency control, and routes messages through the same agent pipeline as the web UI.

![Telegram](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/telegram.png)

### Monitoring & API

**Celery Flower** — Real-time task queue monitor. Track worker status, task throughput, and failure rates for background jobs (document ingestion, email, webhooks).

![Flower](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/flower.png)

**API Documentation** — Auto-generated OpenAPI / Swagger UI at `/docs`. All endpoints documented with request/response schemas, auth requirements, and example payloads.

![API Docs](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/docs_2.png)
