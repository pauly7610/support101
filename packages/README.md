# Packages

This folder contains shared libraries and utilities for all apps in the monorepo.

## Core Packages

- **`shared`**: Pydantic models, types, and frontend utilities for all apps (used for API contracts and analytics)
- **`llm_engine`**: LangChain chains, memory, prompts, and vector store integration (includes analytics support)
- **`observability`**: LangSmith, PromptLayer, OpenTelemetry setup for tracing and metrics

## Enterprise Agent Framework

- **`agent_framework`**: A reusable agent SDK that transforms the RAG + LangChain implementation into a full-featured enterprise agent platform.

### Features
| Feature | Description |
|---------|-------------|
| **Agent Templates** | Swappable blueprints (`SupportAgent`, `TriageAgent`) with custom agent support |
| **Human-in-the-Loop** | Priority queue with SLA tracking, escalation policies, reviewer assignment |
| **Multi-Tenant** | Tier-based limits (FREE→ENTERPRISE), namespace isolation, rate limiting |
| **Governance** | RBAC permissions, complete audit trails, compliance export |

### Quick Start
```python
from packages.agent_framework import create_framework

framework = create_framework()
tenant = await framework.create_tenant("Acme Corp", tier="professional")
agent = framework.create_agent("support_agent", tenant.tenant_id, "Support Bot")
result = await framework.execute(agent, {"query": "How do I reset my password?"})
```

See [agent_framework/README.md](agent_framework/README.md) for full documentation.

---

All packages are production-ready, analytics-enabled, and tested via CI.

See root `DESIGN_SYSTEM.md` for frontend design tokens and shared UI patterns.

---
## Troubleshooting
- For analytics or DB issues, ensure backend is migrated and env vars are set
- For model/schema problems, update `shared` and rerun tests
- For agent framework issues, ensure `OPENAI_API_KEY` is set for LLM calls
