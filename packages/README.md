# Packages

Shared libraries and utilities for all apps in the monorepo.

## `shared`
Pydantic models, constants, and utilities used as API contracts across backend and frontend.

## `llm_engine`
LLM and RAG infrastructure:

| Module | Description |
|--------|-------------|
| `chains/rag_chain.py` | LangChain RAG with Pinecone, citation filtering, exponential backoff |
| `multi_model.py` | Unified `get_chat_model()` — OpenAI, Anthropic, Gemini, Ollama, LiteLLM |
| `vector_store.py` | Pinecone Serverless v3 with integrated reranking + metadata filtering |
| `voice.py` | Whisper STT + OpenAI TTS with full voice chat pipeline |
| `cost_tracker.py` | Per-model token pricing (10+ models), budget alerts, DB-persisted |
| `embeddings.py` | FastEmbed model for local embeddings |

## `agent_framework`
Enterprise agent SDK with 9 blueprints, HITL, multi-tenancy, and continuous learning.

| Feature | Description |
|---------|-------------|
| **9 Agent Blueprints** | Support, triage, data analyst, code review, QA, knowledge manager, sentiment, onboarding, compliance |
| **Human-in-the-Loop** | Priority queue with SLA tracking, escalation policies, reviewer assignment |
| **Multi-Tenant** | Tier-based limits (FREE → ENTERPRISE), namespace isolation, rate limiting |
| **Governance** | RBAC permissions, complete audit trails, compliance export |
| **Continuous Learning** | 4-layer system: Feedback Loop (Pinecone) → Activity Stream (Redis) → Activity Graph (AGE) → Playbook Engine (LangGraph) |
| **A2A Protocol** | Agent-to-Agent interoperability via AgentCard + JSON-RPC 2.0 |
| **MCP Server** | 8 tools exposed via JSON-RPC 2.0 for IDE integration |
| **Observability** | OpenTelemetry tracing, EvalAI integration, Prometheus metrics |

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

All packages are production-ready, tested via CI (197 pytest tests), and gracefully degrade when optional infrastructure (Redis, AGE, LangGraph) is unavailable.
