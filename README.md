# 🧠 Support Intelligence Core (SIC)

[![Build Status](https://img.shields.io/github/actions/workflow/status/pauly7610/support101/ci.yml?branch=main)](https://github.com/pauly7610/support101/actions)
[![License](https://img.shields.io/github/license/pauly7610/support101)](LICENSE)
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

- **FastAPI Backend:** LangChain RAG, ingestion pipeline, Pinecone, HuggingFace/OpenAI support
- **Agent Copilot:** Chrome extension for Zendesk/Intercom
- **Customer Chatbot:** Embeddable widget (Next.js + Tailwind)
- **Shared Models & Design System:** Unified contracts, telemetry, and UI
- **Built for:** Speed, reusability, and modularity

---

## Monorepo Structure

```text
support101/
├── apps/
│   ├── backend/           # FastAPI API (RAG, ingestion, LLM)
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
## Key Features

- **Retrieval-Augmented Generation (RAG):**
  - Query embedding & document search via Pinecone
  - Context-aware generation (HuggingFace or OpenAI LLMs)
  - Source citation for all responses
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

## Quickstart
### 1. Clone & Set Up Environment

```sh
git clone https://github.com/pauly7610/support101
cd support101
cp .env.template .env
```

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

