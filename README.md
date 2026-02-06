# 🧠 Support Intelligence Core (SIC)

[![Build Status](https://img.shields.io/github/actions/workflow/status/pauly7610/support101/ci.yml?branch=main)](https://github.com/pauly7610/support101/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

*A modular, LLM-powered customer support platform for rapid deployment and extensibility.*

---

## 🚀 Visuals

### System Architecture

![Customer Support Platform Architecture](https://raw.githubusercontent.com/veritasautomata/veritasautomata.com/main/static/img/architecture-chatbot.png)
<sub><sup>Reference: Veritas Automata, “Building an Efficient Customer Support Chatbot: Reference Architectures for Azure OpenAI API and Open-Source LLM/Langchain Integration” ([source](https://veritasautomata.com/insights/thought-leadership/build-efficient-chatbot/))</sup></sub>

### UI Examples

- ![Agent Copilot Example](https://user-images.githubusercontent.com/674621/229366721-9b5f2b5b-8f60-4c6e-9b7c-4b2b7d3c7b8e.png)
  <sub><sup>Example Chrome extension copilot UI (replace with your own screenshot)</sup></sub>
- ![Customer Chatbot Example](https://user-images.githubusercontent.com/674621/229366740-1d2b3e2d-9e4e-4b7a-8c8c-2b8c6b6c2a2b.png)
  <sub><sup>Example customer chatbot widget UI (replace with your own screenshot)</sup></sub>

---

## Features

### Async Database & Migrations
- Uses SQLAlchemy async engine with asyncpg driver for PostgreSQL.
- Alembic is configured for async migrations. Always use `postgresql+asyncpg://` in connection URLs.
- To run migrations, set `PYTHONPATH` to the repo root and run:
  ```sh
  export PYTHONPATH=$PWD  # or set PYTHONPATH=%CD% on Windows
  alembic -c apps/backend/alembic.ini upgrade head
  ```
- If you see `InvalidPasswordError`, reset your Postgres password:
  ```sql
  ALTER USER postgres WITH PASSWORD 'yourpassword';
  ```
- See backend/README.md for more details.

---

- **GDPR/CCPA Compliance:** Endpoints `/gdpr_delete` and `/ccpa_optout` with JWT auth for secure data deletion and opt-out, supporting regulatory compliance.
- **Analytics & Reporting:** Escalation tracking, 30-day reporting, and agent/category breakdowns.
- **FastAPI Backend:** LangChain RAG, ingestion pipeline, Pinecone, HuggingFace/OpenAI support
- **Agent Copilot:** Chrome extension for Zendesk/Intercom
- **Customer Chatbot:** Embeddable widget (Next.js + Tailwind)
- **Shared Models & Design System:** Unified contracts, telemetry, and UI
- **Built for:** Speed, reusability, and modularity

## 🚦 New in This Release

- **🤖 Enterprise Agent Framework:** A reusable agent SDK with 9 swappable blueprints, human-in-the-loop queues, multi-tenant deployment, and governance dashboards. See [Agent Framework README](packages/agent_framework/README.md).
- **📊 EvalAI Platform Integration:** Agent workflow tracing, decision auditing, cost tracking, and governance via [`@pauly4010/evalai-sdk`](https://www.npmjs.com/package/@pauly4010/evalai-sdk). Python backend sends traces to EvalAI REST API; JS frontends use the npm SDK directly. See [EvalAI Integration](#evalai-integration) below.
- **🧩 9 Agent Blueprints** (all auto-registered, create via `framework.create_agent(blueprint="name")`):
  - **support_agent** — RAG-powered customer support with intent analysis and escalation
  - **triage_agent** — Intelligent ticket routing and prioritization
  - **data_analyst** — Data analysis with pattern detection, insights, and reporting
  - **code_review** — Automated code review (security, quality, performance)
  - **qa_test** — Test generation, output validation, and regression detection
  - **knowledge_manager** — KB curation with auditing, gap analysis, and deduplication
  - **sentiment_monitor** — Real-time sentiment tracking with escalation triggers
  - **onboarding** — Customer onboarding with personalized checklists and guided setup
  - **compliance_auditor** — PII scanning, policy checks (GDPR/HIPAA/SOC2/CCPA), remediation
- **🧠 Continuous Learning System:** 4-layer learning loop that makes agents smarter over time without model fine-tuning:
  - **Feedback Loop** — HITL outcomes (approve/reject/edit) captured as "golden paths" in Pinecone for future RAG
  - **Activity Stream** — Redis Streams-backed event sourcing for all internal + external activity
  - **Activity Graph** — Apache AGE knowledge graph on Postgres linking customers → tickets → resolutions → articles → agents
  - **Playbook Engine** — LangGraph-based auto-generated resolution workflows from successful traces
  - See [Continuous Learning](#continuous-learning) below.
- **🔗 Inbound Webhooks:** FastAPI endpoints for Zendesk, Slack, Jira, and generic webhooks with HMAC signature verification
- **🖥️ HITL Approval Queue UI:** React component with claim/review/approve/reject workflow, SLA indicators, priority badges, filter tabs, and ARIA accessibility (`apps/customer-bot/src/components/ApprovalQueue.tsx`)
- **📈 Governance Dashboard UI:** React page with agent metrics, HITL stats, SLA compliance, active agents table, and expandable audit log (`apps/customer-bot/src/pages/governance.tsx`)
- **GDPR/CCPA Compliance:** Endpoints `/gdpr_delete` and `/ccpa_optout` with JWT auth for secure data deletion and opt-out, supporting regulatory compliance.
- **Analytics & Reporting:** Escalation tracking, 30-day reporting, and agent/category breakdowns.
- **Compliance UI:** Customer-facing settings and admin dashboard for data/privacy management.
- **Async Test Infrastructure:** Refactored backend tests with async DB mocking, pytest-asyncio, and improved isolation.
- **SQLAlchemy Utilities:** Enhanced DB layer for robust migrations and testability.

---

## Monorepo Structure

```text
support101/
├── apps/
│   ├── backend/           # FastAPI API (RAG, ingestion, LLM, Alembic migrations)
│   ├── agent-copilot/     # React Chrome Extension for agent support
│   └── customer-bot/      # Next.js Chatbot widget
├── packages/
│   ├── shared/            # Pydantic models, constants, utils
│   ├── llm_engine/        # LangChain chains, vector store, prompts
│   ├── agent_framework/   # Enterprise Agent SDK (blueprints, HITL, learning)
│   │   └── learning/      # Feedback loop, activity stream, graph, playbooks
│   └── observability/     # LangSmith, PromptLayer, OpenTelemetry hooks
├── .env.template
├── docker-compose.yml
├── turbo.json
└── README.md
```

---

## Database Migrations & Testing

- **Canonical Alembic migrations directory:**
  - All migration scripts are located in `apps/backend/migrations/versions/`.
  - The Alembic config is `apps/backend/alembic.ini`.
  - Example command to generate a migration (from repo root):
    ```bash
    # On Windows PowerShell
    $env:PYTHONPATH="apps/backend"; alembic -c apps/backend/alembic.ini revision --autogenerate -m "My migration"
    # On Linux/macOS
    PYTHONPATH=apps/backend alembic -c apps/backend/alembic.ini revision --autogenerate -m "My migration"
    ```
  - To apply migrations:
    ```bash
    $env:PYTHONPATH="apps/backend"; alembic -c apps/backend/alembic.ini upgrade head
    ```
- **CI/CD:**
  - The workflow ensures the database exists, runs Alembic migrations, and then runs backend tests.
  - If you see `relation "users" does not exist`, check that migrations ran and the correct DB is targeted.
- **Troubleshooting:**
  - Ensure all relevant directories (`app/`, `app/core/`, `app/auth/`) contain `__init__.py` files.
  - Only one canonical migrations directory should exist: `apps/backend/migrations`.
  - If Alembic does not detect models, check imports in `migrations/env.py` and `PYTHONPATH`.

---

## Configuration & Environment Variables

Before running the backend or frontend, you must set up your environment variables. Copy `.env.example` to `.env` and provide your own API keys and database URLs:

```bash
cp .env.example .env
```

**Required variables:**
- `DATABASE_URL`: Your database connection string (e.g., PostgreSQL, MySQL, SQLite)
- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI models)
- `PINECONE_API_KEY`: Your Pinecone API key (for vector storage)
- `PINECONE_ENVIRONMENT`: Pinecone environment (e.g., `gcp-starter`)
- `SECRET_KEY`: (Backend secret for Flask, Django, etc.)
- `REDIS_URL`: (Optional, for caching, async tasks)

See `.env.example` for all supported variables.

**Note:** Never commit your real API keys or secrets to version control. Use environment variables or a `.env` file that is excluded via `.gitignore`.

---
## Key Features

- **Retrieval-Augmented Generation (RAG):**
  - Query embedding & document search via Pinecone
  - Context-aware generation (HuggingFace or OpenAI LLMs)
  - Source citation for all responses
- **Persistent Analytics:**
  - Escalation analytics stored in PostgreSQL for reliability and reporting
  - Advanced dashboard filters (by user, date range) and visualizations
- **Automated Database Migrations:**
  - Run `python apps/backend/migrations.py` before starting backend
- **Testing & Linting:**
  - Cypress E2E with type definitions (`npm install --save-dev cypress @types/cypress`)
  - Black for Python, strict TypeScript for frontend
- **Production Workflow:**
  - Use `start-all.sh` for full stack startup (migrations, backend, frontend)
  - Set `POSTGRES_URL` for backend analytics

---
## Quickstart

1. Clone repo and install dependencies (Python, Node.js)
2. Set up `.env` files and `POSTGRES_URL`
3. Run DB migrations: `python apps/backend/migrations.py`
4. Start all: `./start-all.sh`
5. Install Cypress types in `apps/customer-bot`: `npm install --save-dev cypress @types/cypress`
6. Access analytics dashboard for advanced filtering and reporting

---
## Troubleshooting
- If you see Cypress or type errors: ensure `@types/cypress` is installed
- Backend analytics not updating? Check DB connection and run migrations
- For more, see individual app READMEs
- **Documentation Ingestion:**
  - Ingest content from public URLs (Firecrawl-ready)
  - Chunk, embed, and store with `/ingest_documentation`
  - Markdown & semantic chunking
- **Agent Copilot (Chrome Extension):**
  - Injected into Zendesk/Intercom UI
  - Auto-detects or pastes customer query
  - Shows suggested reply & source docs
  - One-click copy to reply
- **Customer Chatbot:**
  - Embeddable widget
  - User questions → backend RAG → instant answers
  - Cites doc links for context
- **Shared Infrastructure:**
  - Pydantic models for contracts
  - Telemetry via LangSmith & PromptLayer
  - Modular LangChain chains
  - Unified UI (see `DESIGN_SYSTEM.md`)

---
### 1. Clone & Set Up Environment

```sh
git clone https://github.com/pauly7610/support101
cd support101
```

## ⚠️ Test Suite Note

Some backend tests are marked with `@pytest.mark.xfail` because certain endpoints are not yet implemented or require real API keys (e.g., LLM, analytics, ingest, or compliance endpoints). These tests are expected to fail until the corresponding endpoints are completed and valid keys are provided.

- See `apps/backend/tests/` for details.
- Remove or update the `xfail` marks as endpoints and keys become available.

cp .env.template .env

Fill in your `.env` with:
- `PINECONE_API_KEY`
- `FIRECRAWL_API_KEY`
- `HUGGINGFACE_API_KEY` (or OpenAI)
- `LANGSMITH_API_KEY`, etc.

### 2. Install Dependencies

**Backend:**
```sh
cd apps/backend
pip install -r requirements.txt
```
**Frontends:**
```sh
cd apps/agent-copilot && npm install
cd ../customer-bot && npm install
```

### 3. Run Locally

**Backend:**
```sh
uvicorn apps.backend.main:app --reload
```
**Agent Copilot Extension:**
```sh
cd apps/agent-copilot
npm run dev
```
**Customer Bot Widget:**
```sh
cd apps/customer-bot
npm run dev
```

### 4. Try It Out
- Visit a helpdesk page with the extension running to see the Copilot sidebar
- Open the website widget and ask a question
- Both use `/generate_reply` for grounded answers with source docs

---

## API Endpoints

### Core Endpoints
| Method | Route                  | Description                         |
|--------|------------------------|-------------------------------------|
| GET    | `/health`              | Simple health check                 |
| POST   | `/register`            | Register a new user                 |
| POST   | `/login`               | Login and get JWT token             |
| GET    | `/protected`           | Example protected endpoint          |
| POST   | `/generate_reply`      | Main endpoint for LLM reply         |
| POST   | `/ingest_documentation`| Crawl & embed new documentation     |
| POST   | `/feedback`            | Submit user feedback                |

### Compliance Endpoints (`/v1/compliance`)
| Method | Route                       | Description                              |
|--------|-----------------------------|------------------------------------------|
| POST   | `/v1/compliance/gdpr_delete`| GDPR-compliant data deletion (JWT req)   |
| POST   | `/v1/compliance/ccpa_optout`| CCPA opt-out preference (JWT required)   |

### Analytics Endpoints (`/v1/analytics`)
| Method | Route                              | Description                         |
|--------|------------------------------------|-------------------------------------|
| GET    | `/v1/analytics/escalations`        | Get escalation analytics            |
| GET    | `/v1/analytics/escalations/by-agent`| Escalations grouped by agent       |
| GET    | `/v1/analytics/escalations/by-category`| Escalations grouped by category |

### Agent Framework Endpoints (`/v1`)
| Method | Route                          | Description                              |
|--------|--------------------------------|------------------------------------------|
| GET    | `/v1/agents/blueprints`        | List available agent blueprints          |
| POST   | `/v1/agents`                   | Create an agent from a blueprint         |
| POST   | `/v1/agents/{id}/execute`      | Execute an agent                         |
| GET    | `/v1/governance/dashboard`     | Real-time agent monitoring dashboard     |
| GET    | `/v1/governance/audit`         | Query audit logs                         |
| GET    | `/v1/hitl/queue`               | Get pending human-in-the-loop requests   |
| POST   | `/v1/hitl/queue/{id}/respond`  | Respond to a HITL request                |
| POST   | `/v1/tenants`                  | Create a new tenant                      |
| GET    | `/v1/tenants/{id}/usage`       | Get tenant usage statistics              |

### Webhook Endpoints (`/v1/webhooks`)
| Method | Route                          | Description                              |
|--------|--------------------------------|------------------------------------------|
| POST   | `/v1/webhooks/generic`         | Receive generic webhook events           |
| POST   | `/v1/webhooks/zendesk`         | Receive Zendesk events (tickets, CSAT)   |
| POST   | `/v1/webhooks/slack`           | Receive Slack events (messages, reactions)|
| POST   | `/v1/webhooks/jira`            | Receive Jira events (issues, comments)   |
| GET    | `/v1/webhooks/stats`           | Webhook & activity stream statistics     |

---

## Continuous Learning

The agent framework includes a 4-layer continuous learning system that makes agents smarter over time — **no model fine-tuning required**. Learning happens at the retrieval layer: better context in prompts (golden paths), better routing (graph-informed), and proven step sequences (playbooks).

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│  1. Agent executes using current knowledge (KB + golden paths)         │
│  2. Human reviews (HITL) or customer reacts (CSAT, ticket resolved)   │
│  3. Feedback captured → golden path in Pinecone + graph node           │
│  4. Next execution retrieves proven resolutions + playbook suggestions │
│  5. Repeated patterns auto-generate playbooks (3+ similar successes)   │
└───────────────────────────────────────────────────────────────────────────────┘
```

| Layer | Technology | Purpose |
|---|---|---|
| **Feedback Loop** | Pinecone | HITL outcomes → golden paths for future RAG retrieval |
| **Activity Stream** | Redis Streams | Durable event sourcing for all internal + webhook events |
| **Activity Graph** | Apache AGE (Postgres) | Knowledge graph: Customer→Ticket→Resolution→Article→Agent |
| **Playbook Engine** | LangGraph | Auto-generated resolution workflows from successful traces |

**Graceful degradation:** Every layer falls back silently when its dependency is unavailable (no Redis → in-memory buffer, no AGE → in-memory graph, no LangGraph → sequential execution).

See [Agent Framework README](packages/agent_framework/README.md) for detailed usage examples.

### Validated Performance

The feedback loop has been validated with `FeedbackLoopValidator` — a built-in tool that proves golden paths measurably improve agent performance:

```text
$ python -m packages.agent_framework.learning.feedback_validator --mock

VALIDATION REPORT
─────────────────────────────────────────────────────
  Golden paths stored:        6 (top 60% by confidence)
  Golden path usage rate:     100%
  Avg confidence before:      0.798
  Avg confidence after:       0.836  (+4.8%)
  Avg response time before:   58.8ms
  Avg response time after:    0.2ms  (-99.6%)
  VALIDATION PASSED
```

Run with `--mock` for CI (no API keys needed) or without for live Pinecone + LLM validation.

---

## EvalAI Integration

The agent framework integrates with the [EvalAI Platform](https://ai-evaluation-platform.vercel.app) (`@pauly4010/evalai-sdk`) for workflow tracing, decision auditing, cost tracking, and governance.

### Architecture

```text
┌──────────────────┐  REST API   ┌──────────────┐  npm SDK   ┌──────────────────┐
│ Python Agent     │ ──────────→ │  EvalAI      │ ←───────── │ JS/TS Frontend   │
│ Framework        │  POST       │  Platform    │  import    │ (governance,     │
│ (FastAPI)        │  /api/*     │  (Vercel)    │            │  DAG viz, costs) │
└──────────────────┘             └──────────────┘            └──────────────────┘
```

- **Python backend** → calls EvalAI REST API via `httpx` (async, with retry + backoff)
- **JS frontends** → import `@pauly4010/evalai-sdk` directly for type-safe SDK access

### Setup

1. Add env vars to your `.env`:
   ```
   EVALAI_API_KEY=your-evalai-api-key
   EVALAI_BASE_URL=https://ai-evaluation-platform.vercel.app
   EVALAI_ORGANIZATION_ID=123
   ```

2. The tracer auto-activates when env vars are set. No code changes needed — `AgentFramework` initializes it automatically.

### Python Usage

```python
from packages.agent_framework import (
    AgentFramework,
    EvalAITracer,
    EvalAIDecision,
    EvalAICostRecord,
    check_governance,
    COMPLIANCE_PRESETS,
)

# Framework auto-traces all agent executions
framework = AgentFramework()
result = await framework.execute(agent, {"query": "Help me reset my password"})
# → Workflow trace, agent spans, and timing sent to EvalAI automatically

# Direct tracer usage for custom workflows
tracer = EvalAITracer()
async with tracer.workflow("Custom Pipeline"):
    span = await tracer.start_agent_span("RouterAgent", {"query": "..."})
    await tracer.record_decision(EvalAIDecision(
        agent="RouterAgent",
        type="route",
        chosen="technical_support",
        alternatives=[{"action": "billing", "confidence": 20}],
        confidence=85,
    ))
    await tracer.record_cost(EvalAICostRecord(
        provider="openai", model="gpt-4o", input_tokens=500, output_tokens=200
    ))
    await tracer.end_agent_span(span, {"result": "routed"})

# Governance checks (mirrors EvalAI compliance presets)
gov_result = check_governance(decision, COMPLIANCE_PRESETS["SOC2"])
if gov_result["blocked"]:
    raise RuntimeError(f"Blocked: {gov_result['reasons']}")
```

### What Gets Traced

| Event | EvalAI Endpoint | Automatic? |
|-------|----------------|------------|
| Workflow start/end | `POST /api/traces` | Yes (via `framework.execute()`) |
| Agent execution spans | `POST /api/traces/{id}/spans` | Yes (via `AgentExecutor`) |
| Agent decisions | `POST /api/decisions` | Manual (call `tracer.record_decision()`) |
| LLM token costs | `POST /api/costs` | Manual (call `tracer.record_cost()`) |
| Agent handoffs | `POST /api/traces/{id}/spans` | Manual (call `tracer.record_handoff()`) |
| Workflow DAG definitions | `POST /api/workflows` | Manual (pass `definition` to `start_workflow()`) |

### Graceful Degradation

The tracer silently no-ops when:
- `httpx` is not installed
- Any of the 3 env vars are missing
- The EvalAI API is unreachable (errors are logged, never raised)

---

## Developer Notes
See individual app README.mds for dev details

Uses Turborepo for task orchestration

Docker support in docker-compose.yml (coming soon)

Add new chains or document loaders in packages/llm-engine

Extend observability in packages/observability

🚀 Deployment
 Railway, Render, or AWS-compatible with Docker

 Add CI via GitHub Actions (lint/test/build)

 Staging + production config via env vars

📐 Resources
DESIGN_SYSTEM.md: Shared UI guidelines + tokens

packages/shared: Source of truth for all models/types

turbo.json: Task graph for multi-app orchestration

