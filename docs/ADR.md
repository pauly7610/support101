# Architecture Decision Records (ADR)

This document tracks key architecture decisions for the Support101 backend.

## ADR-2025-05: JWT-Protected Compliance Endpoints & Async Test Infra
- All GDPR/CCPA endpoints require JWT authentication for both customer and admin flows.
- Admin dashboard and compliance UI built for secure data deletion and opt-out.
- Async test infrastructure with pytest-asyncio and SQLAlchemy for robust backend testing.

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
