# Support Intelligence Core Monorepo

A full-stack, LLM-powered customer support platform with:
- FastAPI backend (LangChain RAG, Pinecone, OpenAI, ingestion)
- Chrome extension for agent copilot
- Next.js + Tailwind chatbot widget for customers
- Shared models/utilities and a unified design system

---

## Monorepo Structure

- **`apps/backend`**: FastAPI backend (async, RAG, ingestion, Pinecone, OpenAI)
- **`apps/agent-copilot`**: Chrome extension (React) for agent support
- **`apps/customer-bot`**: Next.js + Tailwind chatbot widget
- **`packages/shared`**: Pydantic models, types, and utilities (used by backend and both frontends)
- **`packages/llm-engine`**: LangChain RAG chain, embeddings, vector store logic
- **`packages/observability`**: Observability integrations (LangSmith, PromptLayer, OTEL)

## Key Features

- **Retrieval-Augmented Generation (RAG)**: Answers are generated from your docs using Pinecone and OpenAI (or HuggingFace) LLMs.
- **Document Ingestion**: Ingest new docs via `/ingest_documentation` endpoint (Firecrawl-ready, chunking included).
- **Agent Copilot**: Chrome sidebar for agents, with real-time suggested replies and KB search.
- **Customer Bot**: Chat widget for customers, powered by the same backend.
- **Unified Design System**: Consistent UI primitives and design tokens across all apps.

## Quickstart

1. **Setup Environment**
   - Copy `.env.template` to `.env` and fill in API keys for Pinecone, OpenAI, Firecrawl, etc.
2. **Install Dependencies**
   - Backend: `pip install -r apps/backend/requirements.txt`
   - Frontends: `npm install` in each app folder
3. **Run Locally**
   - Backend: `uvicorn apps/backend/main:app --reload`
   - Agent Copilot: `npm run dev` in `apps/agent-copilot`
   - Customer Bot: `npm run dev` in `apps/customer-bot`
4. **Try It Out**
   - Open the Copilot sidebar or Customer Bot widget and ask a question
   - Backend will return RAG-powered answers with sources

## Backend Endpoints
- `GET /health` — Health check
- `POST /generate_reply` — Generate an AI reply (used by both frontends)
- `POST /ingest_documentation` — Ingest new docs for RAG

## Developer Notes
- See each app/package `README.md` for further details
- All apps use shared models for type safety and data contracts
- Extend backend for new endpoints, ingestion logic, or TTS as needed
- See `turbo.json` for monorepo task orchestration

---

For design tokens and shared UI, see `DESIGN_SYSTEM.md`.
For advanced deployment, see Docker/Turborepo instructions in this folder.
