# Backend (FastAPI)

This is the FastAPI backend for the Support Intelligence Core.

## Features
- Healthcheck endpoint (`/health`)
- `/generate_reply` endpoint for RAG-powered agent/customer replies (async, with sources)
- `/ingest_documentation` endpoint for crawling and chunking docs (Firecrawl integration ready)
- LangChain, HuggingFace/FastEmbed, Pinecone vector store
- Uses shared Pydantic models from `packages/shared`
- CORS enabled for frontend integration

## Integration
- Serves as API for both customer bot and agent copilot frontends
- Returns structured ticket, user, and reply data for design system-driven UIs

## Setup & Usage
1. Copy `.env.template` to `.env` and fill in API keys
2. `pip install -r requirements.txt`
3. `uvicorn main:app --reload`

## Dev
- See root README for Docker/dev instructions and environment setup
- Update Pinecone/OpenAI keys as needed
- Extend endpoints for new RAG, ingestion, or TTS features
