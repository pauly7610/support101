# Architecture Decision Records (ADR)

This document tracks key architecture decisions for Support Intelligence Core.

---

## ADR-001: Use FastAPI for Backend
- **Date:** 2025
- **Decision:** FastAPI enables async endpoints, automatic OpenAPI docs, and high performance.
- **Status:** Active

## ADR-002: Use Pinecone for Vector Store
- **Date:** 2025
- **Decision:** Pinecone provides managed, scalable vector storage with cosine similarity.
- **Details:** Index `support101`, 768 dimensions. Upgraded to Pinecone Serverless v3 with integrated reranking (bge-reranker-v2-m3) and metadata filtering v2.
- **Status:** Active

## ADR-003: Prometheus for Metrics
- **Date:** 2025
- **Decision:** Exposes LLM response times, vector store cache hits, API error rates at `/metrics`.
- **Status:** Active

## ADR-004: JWT for Authentication
- **Date:** 2025
- **Decision:** All protected endpoints require JWT validation middleware. Per-endpoint rate limiting added.
- **Status:** Active

## ADR-005: JWT-Protected Compliance Endpoints & Async Test Infra
- **Date:** 2025-05
- **Decision:** All GDPR/CCPA endpoints require JWT authentication. Async test infrastructure with pytest-asyncio and SQLAlchemy.
- **Status:** Active

## ADR-006: Migrate from ESLint + Prettier to Biome
- **Date:** 2026-02
- **Decision:** Replace ESLint 8 + Prettier with Biome for unified linting, formatting, and import sorting across all frontend apps. Single `biome.json` config at project root.
- **Rationale:** Faster execution, single tool, consistent config, better monorepo support.
- **Status:** Active

## ADR-007: Migrate from npm to pnpm Workspaces
- **Date:** 2026-02
- **Decision:** Migrate to pnpm with `pnpm-workspace.yaml` covering `apps/agent-copilot`, `apps/customer-bot`, and `apps/admin-dashboard`. 50-70% disk savings via content-addressable storage.
- **Status:** Active

## ADR-008: Migrate from Black + flake8 to Ruff
- **Date:** 2026-02
- **Decision:** Replace Black, flake8, and isort with Ruff for Python linting and formatting. Configured in `pyproject.toml`.
- **Status:** Active

## ADR-009: Multi-Model LLM Provider Abstraction
- **Date:** 2026-02
- **Decision:** Unified `get_chat_model()` abstraction supporting OpenAI, Anthropic Claude, Google Gemini, Ollama, and LiteLLM. Provider selection via config, not code changes.
- **Status:** Active

## ADR-010: 4-Layer Continuous Learning System
- **Date:** 2026-02
- **Decision:** Implement continuous learning without model fine-tuning via 4 layers:
  1. **Feedback Loop** (Pinecone) — HITL outcomes as golden paths
  2. **Activity Stream** (Redis Streams) — Durable event sourcing
  3. **Activity Graph** (Apache AGE) — Knowledge graph linking entities
  4. **Playbook Engine** (LangGraph) — Auto-generated resolution workflows
- **Graceful degradation:** Each layer falls back to in-memory when infrastructure unavailable.
- **Status:** Active

## ADR-011: A2A Protocol for Agent Interoperability
- **Date:** 2026-02
- **Decision:** Implement Agent-to-Agent protocol via AgentCard discovery (`/.well-known/agent.json`) and JSON-RPC 2.0 task dispatch (`/a2a`).
- **Status:** Active

## ADR-012: MCP Server for IDE Integration
- **Date:** 2026-02
- **Decision:** Expose 8 agent framework tools via JSON-RPC 2.0 over stdio for IDE/editor integration (Model Context Protocol).
- **Status:** Active

## ADR-013: LLM Cost Tracking
- **Date:** 2026-02
- **Decision:** Per-model token pricing (10+ models), per-tenant breakdown, budget alerts with configurable thresholds. PostgreSQL-persisted with in-memory write-through cache.
- **Status:** Active

## ADR-014: Next.js 15 + React 19 Frontend
- **Date:** 2026-02
- **Decision:** Upgrade customer-bot and admin-dashboard to Next.js 15 with React 19. Use Vercel AI SDK for streaming chat via `useChat()` hook.
- **Status:** Active

## ADR-015: Production Docker Compose
- **Date:** 2026-02
- **Decision:** Multi-stage Docker builds with non-root users, PostgreSQL 16, Redis 7, resource limits, and healthchecks. Separate dev/test/prod compose files.
- **Status:** Active

## ADR-016: EvalAI Integration
- **Date:** 2026-02
- **Decision:** Integrate `@pauly4010/evalai-sdk` for workflow tracing, decision auditing, and governance checks. Python backend uses httpx REST client; JS frontends import npm SDK directly. Silently no-ops when env vars unset.
- **Status:** Active

## ADR-017: Vitest + React Testing Library for Frontend Tests
- **Date:** 2026-02
- **Decision:** Use Vitest with `@vitejs/plugin-react` (automatic JSX runtime) and React Testing Library across all 3 frontend apps. 8 test suites total.
- **Status:** Active

---
Add new ADRs below as architectural changes are made.
