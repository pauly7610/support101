# Packages

This folder contains shared libraries and utilities for all apps in the monorepo.

- `shared`: Pydantic models, types, and frontend utilities for all apps (used for API contracts and analytics)
- `llm-engine`: LangChain chains, memory, prompts, and vector store integration (includes analytics support)
- `observability`: LangSmith, PromptLayer, OpenTelemetry setup for tracing and metrics

All packages are production-ready, analytics-enabled, and tested via CI.

See root `DESIGN_SYSTEM.md` for frontend design tokens and shared UI patterns.

---
## Troubleshooting
- For analytics or DB issues, ensure backend is migrated and env vars are set
- For model/schema problems, update `shared` and rerun tests
