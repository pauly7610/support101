# Support Intelligence Core (SIC)

[![Build Status](https://img.shields.io/github/actions/workflow/status/pauly7610/support101/ci.yml?branch=main)](https://github.com/pauly7610/support101/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**A modular, LLM-powered customer support platform with RAG, multi-model AI, agent orchestration, and continuous learning.**

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Frontend Apps (React / Next.js 15)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Customer Bot │  │Agent Copilot │  │Admin Dashboard│  │  Demo Video  │   │
│  │  (Next.js)   │  │  (Chrome Ext)│  │  (Next.js)   │  │  (Remotion)  │   │
│  │  Port 3000   │  │  Extension   │  │  Port 3002   │  │              │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────────────┘   │
│         │ Vercel AI SDK    │ WebSocket        │ REST                       │
├─────────┴──────────────────┴─────────────────┴────────────────────────────┤
│                        FastAPI Backend (Port 8000)                         │
│  ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ RAG Engine │ │  Agents  │ │   HITL   │ │Governance│ │   Voice I/O  │  │
│  │ /generate  │ │ /v1/agent│ │ /v1/hitl │ │ /v1/gov  │ │  /v1/voice   │  │
│  ├────────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├──────────────┤  │
│  │  A2A Proto │ │Cost Track│ │ Webhooks │ │Analytics │ │  Compliance  │  │
│  │ /a2a       │ │ /costs   │ │ /webhooks│ │/analytics│ │ /compliance  │  │
│  └────────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
├───────────────────────────────────────────────────────────────────────────┤
│                         Packages (Shared Libraries)                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │
│  │   LLM Engine     │  │ Agent Framework  │  │    Shared Models       │  │
│  │ Multi-model RAG  │  │ 9 Blueprints     │  │ Pydantic contracts     │  │
│  │ Pinecone v3      │  │ Tool calling     │  │ Constants & utils      │  │
│  │ Voice (Whisper)  │  │ Continuous learn  │  │                        │  │
│  │ Cost tracking    │  │ OTEL tracing     │  │                        │  │
│  └──────────────────┘  │ A2A protocol     │  └────────────────────────┘  │
│                        │ MCP server       │                               │
│                        └──────────────────┘                               │
├───────────────────────────────────────────────────────────────────────────┤
│                         Infrastructure                                    │
│  PostgreSQL 16 │ Redis 7 │ Pinecone │ Apache AGE │ Prometheus │ Docker   │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Features

### AI & LLM
- **Multi-model RAG** — OpenAI, Anthropic Claude, Google Gemini, Ollama, LiteLLM via unified `get_chat_model()`
- **Pinecone Serverless v3** — Integrated reranking (bge-reranker-v2-m3), metadata filtering v2, namespace isolation, GDPR delete
- **Vercel AI SDK** — Streaming chat via `useChat()` hook with sentiment analysis and source citations
- **Structured tool calling** — `ToolRegistry` with OpenAI/Anthropic schema converters, parallel execution, 4 built-in tools
- **Voice I/O** — Whisper STT + OpenAI TTS with full voice chat pipeline (audio in → RAG → audio out)

### Agent Framework
- **9 agent blueprints** — support, triage, data analyst, code review, QA test, knowledge manager, sentiment monitor, onboarding, compliance auditor
- **Human-in-the-loop (HITL)** — Approval queue with claim/review/approve/reject, SLA indicators, priority badges
- **Continuous learning** — 4-layer system: Feedback Loop (Pinecone) → Activity Stream (Redis) → Activity Graph (Apache AGE) → Playbook Engine (LangGraph)
- **A2A Protocol** — Agent-to-Agent interoperability via AgentCard discovery + JSON-RPC 2.0 task dispatch
- **MCP Server** — 8 tools exposed via JSON-RPC 2.0 over stdio for IDE/editor integration

### Observability & Governance
- **OpenTelemetry tracing** — Traceloop SDK + raw OTEL fallback with specialized spans for LLM calls, vector search, agent execution
- **Prometheus metrics** — LLM response times, vector store cache hits, API error rates
- **LLM cost tracking** — Per-model pricing (10+ models), per-tenant breakdown, budget alerts, cost dashboard API
- **EvalAI integration** — Workflow tracing, decision auditing, governance checks via `@pauly4010/evalai-sdk`
- **Governance dashboard** — Agent metrics, HITL stats, SLA compliance, audit log

### Infrastructure
- **Multi-tenant** — Tenant isolation with resource limits, API key management, usage tracking
- **GDPR/CCPA compliance** — Data deletion endpoints, opt-out mechanisms, chat log anonymization
- **Production Docker** — Multi-stage builds, non-root users, postgres 16, redis 7, resource limits, healthchecks
- **Webhooks** — Zendesk, Slack, Jira, generic with HMAC signature verification

### Frontend
- **Customer chatbot** — Next.js 15 + React 19 + Tailwind, dark mode, glass morphism, streaming chat, voice input
- **Agent copilot** — Chrome extension for Zendesk/Intercom with real-time WebSocket suggestions
- **Admin dashboard** — KB management, agent config, cost tracking, voice config, settings (6 tabs)
- **Demo video** — Remotion project with 7 animated scenes showcasing all features

### Developer Experience
- **pnpm workspaces** — Monorepo with 4 frontend apps
- **Biome** — Replaced ESLint 8 + Prettier with single config (linting, formatting, import sorting)
- **Vitest + RTL** — 6 frontend unit test suites
- **Cypress E2E** — 27 tests covering approval queue, governance dashboard, chat widget
- **Integration tests** — 20+ tests covering feedback loop, activity stream, graph, playbooks, RAG, MCP, WebSocket
- **Ruff** — Python linting (replaced black + flake8 + isort)

---

## Monorepo Structure

```text
support101/
├── apps/
│   ├── backend/              # FastAPI API server
│   │   ├── app/
│   │   │   ├── analytics/    # Escalation analytics + cost tracking
│   │   │   ├── auth/         # JWT authentication
│   │   │   ├── compliance/   # GDPR/CCPA endpoints
│   │   │   ├── core/         # DB, cache, config
│   │   │   ├── voice/        # Voice I/O endpoints (Whisper + TTS)
│   │   │   └── websocket/    # WebSocket copilot server
│   │   ├── migrations/       # Alembic migration scripts
│   │   └── main.py           # FastAPI app entry point
│   ├── customer-bot/         # Next.js 15 customer chat widget
│   │   ├── src/
│   │   │   ├── components/   # ChatWidget, ApprovalQueue, GovernanceDashboard
│   │   │   ├── hooks/        # useStreamingChat, useVoiceChat, useThemeDetection
│   │   │   └── pages/        # Next.js pages + /api/chat streaming route
│   │   └── cypress/          # E2E tests (27 specs)
│   ├── agent-copilot/        # Chrome extension (React + Webpack)
│   ├── admin-dashboard/      # Admin app (Next.js 15, port 3002)
│   └── demo-video/           # Remotion product demo (7 scenes)
├── packages/
│   ├── shared/               # Pydantic models, constants, utils
│   ├── llm_engine/           # LLM & RAG
│   │   ├── chains/           # RAG chain with LangChain
│   │   ├── multi_model.py    # Provider abstraction (5 providers)
│   │   ├── vector_store.py   # Pinecone v3 with reranking
│   │   ├── voice.py          # Whisper STT + OpenAI TTS
│   │   ├── cost_tracker.py   # Token counting + budget alerts
│   │   └── embeddings.py     # FastEmbed model
│   └── agent_framework/      # Enterprise agent SDK
│       ├── core/             # AgentExecutor, tool calling
│       ├── blueprints/       # 9 agent blueprints
│       ├── hitl/             # Human-in-the-loop manager
│       ├── learning/         # Feedback, stream, graph, playbooks
│       ├── observability/    # OTEL tracing, EvalAI tracer
│       ├── a2a/              # A2A protocol (AgentCard + JSON-RPC)
│       ├── mcp_server.py     # MCP server (8 tools)
│       └── sdk.py            # Framework entry point
├── tests/
│   └── integration/          # 20+ integration tests
├── docs/
│   └── openapi.yaml          # OpenAPI 3.0 spec (80+ endpoints)
├── biome.json                # Biome linter/formatter config
├── pyproject.toml            # Python deps + ruff config (uv-compatible)
├── docker-compose.prod.yml   # Production Docker Compose
├── docker-compose.dev.yml    # Development Docker Compose
└── pnpm-workspace.yaml       # pnpm workspace config
```

---

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 20+ with pnpm (`corepack enable`)
- PostgreSQL 16
- Redis 7 (optional, for caching + activity stream)

### 1. Clone & Configure

```bash
git clone https://github.com/pauly7610/support101
cd support101
cp .env.example .env
# Edit .env with your API keys (see Environment Variables below)
```

### 2. Install Dependencies

```bash
# Python backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Frontend apps
pnpm install
```

### 3. Database Setup

```bash
# Create database
createdb support101

# Run migrations
PYTHONPATH=$PWD alembic -c apps/backend/alembic.ini upgrade head
# Windows: $env:PYTHONPATH=$PWD; alembic -c apps/backend/alembic.ini upgrade head
```

### 4. Run Locally

```bash
# Backend (port 8000)
uvicorn apps.backend.main:app --reload

# Customer chatbot (port 3000)
pnpm --filter customer-bot dev

# Agent copilot extension
pnpm --filter agent-copilot dev

# Admin dashboard (port 3002)
pnpm --filter admin-dashboard dev
```

### 5. Production (Docker)

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `OPENAI_API_KEY` | Yes | OpenAI API key (GPT, Whisper, TTS) |
| `PINECONE_API_KEY` | Yes | Pinecone vector store API key |
| `SECRET_KEY` | Yes | JWT signing secret |
| `REDIS_URL` | No | Redis for caching + activity stream |
| `PINECONE_NAMESPACE` | No | Namespace for tenant isolation |
| `PINECONE_RERANK_ENABLED` | No | Enable Pinecone reranking (default: true) |
| `ANTHROPIC_API_KEY` | No | Anthropic Claude models |
| `GOOGLE_API_KEY` | No | Google Gemini models |
| `VOICE_ENABLED` | No | Enable voice features (default: true) |
| `VOICE_TTS_VOICE` | No | TTS voice: alloy, echo, fable, onyx, nova, shimmer |
| `LLM_BUDGET_MONTHLY_USD` | No | Monthly LLM budget in USD (default: 100) |
| `LLM_BUDGET_ALERT_THRESHOLD` | No | Alert at this % of budget (default: 0.8) |
| `A2A_BASE_URL` | No | Base URL for A2A Agent Card |
| `EVALAI_API_KEY` | No | EvalAI platform API key |
| `EVALAI_BASE_URL` | No | EvalAI platform URL |
| `EVALAI_ORGANIZATION_ID` | No | EvalAI organization ID |
| `ACTIVITY_GRAPH_NAME` | No | Apache AGE graph name |
| `TRACELOOP_API_KEY` | No | Traceloop/OTEL API key |

See `.env.example` for the complete list with descriptions.

> **Security:** Never commit API keys. Use `.env` files excluded via `.gitignore`.

---

## API Endpoints

Full OpenAPI spec: [`docs/openapi.yaml`](docs/openapi.yaml) (80+ endpoints)

### Core
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Health check |
| POST | `/register` | Register user |
| POST | `/login` | Login (JWT) |
| POST | `/generate_reply` | RAG-powered reply with citations |
| POST | `/ingest_documentation` | Ingest PDF/MD/TXT to vector store |
| POST | `/feedback` | Submit user feedback |

### Agents (`/v1`)
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/v1/blueprints` | List agent blueprints |
| POST | `/v1/agents` | Create agent from blueprint |
| POST | `/v1/agents/{id}/execute` | Execute agent |
| GET | `/v1/governance/dashboard` | Governance metrics |
| GET | `/v1/governance/audit` | Audit logs |
| GET | `/v1/hitl/queue` | HITL review queue |
| POST | `/v1/hitl/queue/{id}/respond` | Approve/reject HITL request |
| POST | `/v1/tenants` | Create tenant |
| GET | `/v1/tenants/{id}/usage` | Tenant usage stats |

### Voice I/O (`/v1/voice`)
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/v1/voice/transcribe` | Speech-to-text (Whisper) |
| POST | `/v1/voice/synthesize` | Text-to-speech (TTS) |
| POST | `/v1/voice/chat` | Full voice pipeline: audio → RAG → audio |
| GET | `/v1/voice/status` | Voice feature availability |

### Cost Tracking (`/v1/analytics/costs`)
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/v1/analytics/costs` | Cost dashboard (spend, budget, breakdowns) |
| GET | `/v1/analytics/costs/tenant` | Per-tenant cost breakdown |
| POST | `/v1/analytics/costs/record` | Record LLM usage event |

### A2A Protocol
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/.well-known/agent.json` | Agent Card discovery |
| POST | `/a2a` | JSON-RPC 2.0 task dispatch |

### Webhooks (`/v1/webhooks`)
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/v1/webhooks/zendesk` | Zendesk events |
| POST | `/v1/webhooks/slack` | Slack events |
| POST | `/v1/webhooks/jira` | Jira events |
| POST | `/v1/webhooks/generic` | Generic webhook |

### Compliance (`/v1/compliance`)
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/v1/compliance/gdpr_delete` | GDPR data deletion |
| POST | `/v1/compliance/ccpa_optout` | CCPA opt-out |

### WebSocket
| Protocol | Route | Description |
|----------|-------|-------------|
| WS | `/ws/copilot` | Real-time agent suggestions (JWT auth) |

---

## Continuous Learning

4-layer system that makes agents smarter over time — **no model fine-tuning required**:

```text
┌─────────────────────────────────────────────────────────────────────┐
│  1. Agent executes using current knowledge (KB + golden paths)     │
│  2. Human reviews (HITL) or customer reacts (CSAT, resolved)       │
│  3. Feedback captured → golden path in Pinecone + graph node       │
│  4. Next execution retrieves proven resolutions + playbooks        │
│  5. Repeated patterns auto-generate playbooks (3+ successes)       │
└─────────────────────────────────────────────────────────────────────┘
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Feedback Loop** | Pinecone | HITL outcomes → golden paths for future RAG |
| **Activity Stream** | Redis Streams | Durable event sourcing for all events |
| **Activity Graph** | Apache AGE | Knowledge graph: Customer→Ticket→Resolution→Agent |
| **Playbook Engine** | LangGraph | Auto-generated resolution workflows |

**Graceful degradation:** Every layer falls back silently (no Redis → memory, no AGE → memory, no LangGraph → sequential).

### Validated Performance

```text
$ python -m packages.agent_framework.learning.feedback_validator --mock

VALIDATION REPORT
─────────────────────────────────────────────────────
  Golden paths stored:        6 (top 60% by confidence)
  Avg confidence after:       0.836  (+4.8%)
  Avg response time after:    0.2ms  (-99.6%)
  VALIDATION PASSED
```

---

## EvalAI Integration

Integrates with [EvalAI Platform](https://ai-evaluation-platform.vercel.app) for workflow tracing, decision auditing, and governance.

```text
┌──────────────────┐  REST API   ┌──────────────┐  npm SDK   ┌──────────────────┐
│ Python Agent     │ ──────────→ │  EvalAI      │ ←───────── │ JS/TS Frontend   │
│ Framework        │  httpx      │  Platform    │  import    │ (governance,     │
│ (FastAPI)        │  async      │  (Vercel)    │            │  DAG viz, costs) │
└──────────────────┘             └──────────────┘            └──────────────────┘
```

Auto-activates when `EVALAI_API_KEY`, `EVALAI_BASE_URL`, and `EVALAI_ORGANIZATION_ID` are set. Silently no-ops when unavailable.

---

## Testing

```bash
# Backend integration tests
pytest tests/ -v

# Frontend unit tests
pnpm --filter customer-bot test
pnpm --filter agent-copilot test

# Cypress E2E
pnpm --filter customer-bot exec cypress run

# Lint (Biome for JS/TS, Ruff for Python)
pnpm --filter customer-bot lint
ruff check packages/ apps/backend/

# Feedback loop validation
python -m packages.agent_framework.learning.feedback_validator --mock
```

---

## Deployment

### Docker Compose (Production)

```bash
docker compose -f docker-compose.prod.yml up -d
```

Includes: PostgreSQL 16, Redis 7, backend (2 workers), customer-bot, agent-copilot — all with healthchecks, resource limits, and restart policies.

### Manual

- **Backend:** Railway, Render, or any Docker host
- **Frontend:** Vercel (Next.js) or static hosting
- **CI:** GitHub Actions (lint → test → build)

---

## Resources

- [`docs/openapi.yaml`](docs/openapi.yaml) — OpenAPI 3.0 spec (80+ endpoints)
- [`packages/agent_framework/README.md`](packages/agent_framework/README.md) — Agent framework docs
- [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) — Shared UI guidelines
- [`mcp-config.json`](mcp-config.json) — MCP client configuration
- [`biome.json`](biome.json) — Biome linter/formatter config
- [`pyproject.toml`](pyproject.toml) — Python project config (uv-compatible)

