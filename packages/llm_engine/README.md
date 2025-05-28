# LLM Engine Package

LangChain-based engine for RAG, embeddings, and vector store integration (with analytics and compliance).

## Ecosystem Updates
- Supports GDPR/CCPA compliance endpoints (RAG chain integration)
- Analytics escalation tracking and reporting
- Async test infra and SQLAlchemy utilities

## Modules
- `chains.py`: RAGChain for retrieval-augmented generation (async, with sources)
- `chains/rag_chain.py`: RAG with Pinecone, error handling, citation support (cosine similarity threshold 0.75)
- `embeddings.py`: HuggingFace and FastEmbed embedding utilities
- `vector_store.py`: Pinecone vector store management, upsert, and query

## Usage

- Backend and LLM engine are fully async, using asyncpg and SQLAlchemy async engine.
- Alembic migrations are async-compatible (see backend/README.md for operational details).

- Used by FastAPI backend for `/generate_reply` and ingestion endpoints
- Import RAGChain and embedding/vector store utilities for new backend features
- Analytics and citation support for compliance and reporting
