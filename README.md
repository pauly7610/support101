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

- **GDPR/CCPA Compliance:** Endpoints `/gdpr_delete` and `/ccpa_optout` with JWT auth for secure data deletion and opt-out, supporting regulatory compliance.
- **Analytics & Reporting:** Escalation tracking, 30-day reporting, and agent/category breakdowns.
- **FastAPI Backend:** LangChain RAG, ingestion pipeline, Pinecone, HuggingFace/OpenAI support
- **Agent Copilot:** Chrome extension for Zendesk/Intercom
- **Customer Chatbot:** Embeddable widget (Next.js + Tailwind)
- **Shared Models & Design System:** Unified contracts, telemetry, and UI
- **Built for:** Speed, reusability, and modularity

## 🚦 New in This Release

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
│   ├── llm-engine/        # LangChain chains, vector store, prompts
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
| Method | Route                  | Description                         |
|--------|------------------------|-------------------------------------|
| GET    | `/health`              | Simple health check                 |
| POST   | `/generate_reply`      | Main endpoint for LLM reply         |
| POST   | `/ingest_documentation`| Crawl & embed new documentation     |

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

