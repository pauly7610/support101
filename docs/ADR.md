# Architecture Decision Records (ADR)

This document tracks key architecture decisions for the Support101 backend.

## ADR-001: Use FastAPI for Backend
- FastAPI enables async endpoints, automatic OpenAPI docs, and high performance.

## ADR-002: Use Pinecone for Vector Store
- Pinecone provides managed, scalable vector storage with cosine similarity.
- Index: `support101`, 768 dimensions, environment: `gcp-starter`.

## ADR-003: Prometheus for Metrics
- Exposes LLM response times, vector store cache hits, API error rates at `/metrics`.

## ADR-004: JWT for Authentication
- All protected endpoints require JWT validation middleware.

---
Add new ADRs below as architectural changes are made.
