# LLM Engine Package

LangChain-based engine for RAG, embeddings, and vector store integration.

## Modules
- `chains.py`: RAGChain for retrieval-augmented generation (async, with sources)
- `embeddings.py`: HuggingFace and FastEmbed embedding utilities
- `vector_store.py`: Pinecone vector store management, upsert, and query

## Usage
- Used by FastAPI backend for `/generate_reply` and ingestion endpoints
- Import RAGChain and embedding/vector store utilities for new backend features
