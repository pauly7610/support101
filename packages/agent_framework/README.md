# Enterprise Agent Framework

A reusable agent SDK for Support101 that transforms the existing RAG + LangChain implementation into a full-featured enterprise agent platform.

## Features

### 1. Agent Template System
Swappable "agent blueprints" that define agent behavior:

- **SupportAgent**: RAG-powered customer support with intent analysis, knowledge retrieval, and escalation
- **TriageAgent**: Intelligent ticket routing and prioritization

Create custom blueprints by extending `BaseAgent`:

```python
from packages.agent_framework import BaseAgent, AgentBlueprint, AgentConfig

class MyCustomAgent(BaseAgent):
    async def plan(self, state):
        # Determine next action
        return {"action": "my_action", "action_input": {...}}
    
    async def execute_step(self, state, action):
        # Execute the action
        return {"result": "..."}
    
    def should_continue(self, state):
        return state.current_step < self.config.max_iterations

MyBlueprint = AgentBlueprint(
    name="my_agent",
    agent_class=MyCustomAgent,
    description="My custom agent",
    default_config={"max_iterations": 5},
)
```

### 2. Human-in-the-Loop Queue
Formalized escalation logic with SLA tracking:

```python
from packages.agent_framework import HITLManager, HITLPriority

# Request human approval
request = await hitl_manager.request_approval(
    agent=agent,
    action="Send refund",
    context={"amount": 100, "reason": "Product defect"},
)

# Reviewer responds
await hitl_manager.provide_response(
    request_id=request.request_id,
    response={"decision": "approve"},
    reviewer_id="reviewer_123",
)
```

Features:
- Priority-based queuing (critical, high, medium, low)
- SLA tracking with breach notifications
- Automatic assignment to available reviewers
- Escalation policies with configurable rules

### 3. Multi-Tenant Agent Deployment
Isolated agent instances per customer:

```python
from packages.agent_framework import TenantManager, TenantTier

# Create a tenant
tenant = await tenant_manager.create_tenant(
    name="Acme Corp",
    tier=TenantTier.PROFESSIONAL,
    auto_activate=True,
)

# Tenant-isolated execution
async with isolator.isolation_scope(tenant.tenant_id):
    result = await executor.execute(agent, input_data)
```

Features:
- Tier-based resource limits (FREE, STARTER, PROFESSIONAL, ENTERPRISE)
- Rate limiting per tenant
- Namespace isolation for vector stores
- Usage tracking and quota enforcement

### 4. Agent Governance Dashboard
Real-time monitoring and audit trails:

```python
from packages.agent_framework import AuditLogger, AgentPermissions

# Query audit logs
events = audit_logger.query(
    tenant_id="tenant_123",
    event_type=AuditEventType.EXECUTION_COMPLETED,
    limit=100,
)

# Check permissions
has_access = permissions.check_permission(
    agent_id="agent_123",
    resource="tool:escalate_to_human",
    required_level=PermissionLevel.EXECUTE,
)
```

Features:
- Complete audit trail for all agent actions
- Role-based access control (RBAC)
- Permission inheritance
- Compliance reporting and export

## Quick Start

```python
from packages.agent_framework import create_framework

# Initialize the framework
framework = create_framework()

# Create a tenant
tenant = await framework.create_tenant("Acme Corp", tier="professional")

# Create an agent
agent = framework.create_agent(
    blueprint="support_agent",
    tenant_id=tenant.tenant_id,
    name="Support Bot",
)

# Execute the agent
result = await framework.execute(
    agent,
    {"query": "How do I reset my password?"}
)

print(result["output"])
```

## API Endpoints

The framework provides FastAPI routers for all functionality:

### Agents API (`/agents`)
- `GET /agents/blueprints` - List available blueprints
- `POST /agents` - Create an agent
- `GET /agents` - List agents
- `POST /agents/{id}/execute` - Execute an agent

### HITL API (`/hitl`)
- `GET /hitl/queue` - Get pending requests
- `POST /hitl/queue/{id}/respond` - Respond to a request
- `POST /hitl/escalate` - Manual escalation

### Governance API (`/governance`)
- `GET /governance/dashboard` - Real-time dashboard
- `GET /governance/audit` - Query audit logs
- `POST /governance/roles/assign` - Assign roles

### Tenants API (`/tenants`)
- `POST /tenants` - Create a tenant
- `GET /tenants/{id}/usage` - Get usage stats
- `POST /tenants/{id}/activate` - Activate tenant

## Integration with Backend

Add the routers to your FastAPI app:

```python
from packages.agent_framework.api import (
    agents_router,
    governance_router,
    hitl_router,
    tenants_router,
)

app.include_router(agents_router, prefix="/v1")
app.include_router(governance_router, prefix="/v1")
app.include_router(hitl_router, prefix="/v1")
app.include_router(tenants_router, prefix="/v1")
```

### 5. Continuous Learning System

Agents get smarter over time through a 4-layer learning loop — no model fine-tuning required:

```text
Agent Executes → Human Reviews → Feedback Captured → Knowledge Updated → Next Execution Smarter
```

#### Feedback Loop
Every HITL outcome (approve/reject/edit) is captured as a "golden path" in Pinecone:

```python
# Automatic — happens inside HITLManager.provide_response()
# When a reviewer approves, the full trace becomes a golden path
# that future RAG queries can retrieve.

# Manual — record external signals
await framework.record_feedback(
    ticket_id="T-123",
    score=5.0,  # CSAT score
    trace={"input_query": "How to reset password?", ...},
    tenant_id="acme",
)

# Search proven resolutions
paths = await framework.search_golden_paths(
    query="password reset",
    tenant_id="acme",
    top_k=3,
)
```

#### Activity Stream (Redis Streams)
All events (internal + external webhooks) flow into durable Redis Streams:

```python
# Internal events are bridged automatically via EventBus
# External events arrive via webhook endpoints:
#   POST /v1/webhooks/zendesk
#   POST /v1/webhooks/slack
#   POST /v1/webhooks/jira
#   POST /v1/webhooks/generic
```

#### Activity Graph (Apache AGE on Postgres)
A knowledge graph links customers, tickets, resolutions, articles, and agents:

```python
# Automatic — resolutions are recorded when golden paths are created
# Query the graph directly:
journey = await framework.activity_graph.get_customer_journey("customer_123")
similar = await framework.activity_graph.find_similar_resolutions(category="billing")
```

#### Playbook Engine (LangGraph)
Auto-generated resolution workflows derived from successful traces:

```python
# Suggest a playbook for a category
suggestions = await framework.suggest_playbook("billing", tenant_id="acme")

# Extract new playbooks from graph patterns
new_playbooks = await framework.extract_playbooks("billing", tenant_id="acme")

# Playbooks are also suggested automatically before agent execution
# via AgentExecutor when input_data contains a "category" key
```

**Graceful degradation:** No Redis → in-memory buffer. No AGE → in-memory graph. No LangGraph → sequential execution. No Pinecone → golden paths in memory only.

## Architecture

```
packages/agent_framework/
├── core/                    # Core agent infrastructure
│   ├── base_agent.py       # BaseAgent abstract class
│   ├── agent_registry.py   # Blueprint & instance registry
│   └── agent_executor.py   # Execution with lifecycle management
├── templates/               # Agent blueprints (9 built-in)
│   ├── support_agent.py    # RAG-powered support agent
│   ├── triage_agent.py     # Ticket routing agent
│   ├── data_analyst_agent.py
│   ├── code_review_agent.py
│   ├── qa_test_agent.py
│   ├── knowledge_manager_agent.py
│   ├── sentiment_monitor_agent.py
│   ├── onboarding_agent.py
│   └── compliance_auditor_agent.py
├── learning/                # Continuous learning system
│   ├── feedback_loop.py    # Golden path capture from HITL outcomes
│   ├── activity_stream.py  # Redis Streams event sourcing
│   ├── graph.py            # Apache AGE knowledge graph
│   ├── graph_models.py     # Node/edge type definitions
│   ├── playbook_engine.py  # LangGraph playbook compilation
│   └── playbook_models.py  # Playbook data models
├── services/                # Shared service clients
│   ├── database.py         # Async Postgres (SQLAlchemy)
│   ├── vector_store.py     # Pinecone vector store
│   ├── external_api.py     # External HTTP client
│   └── llm_helpers.py      # LLM retry + cost tracking
├── governance/              # Permissions & audit
│   ├── permissions.py      # RBAC system
│   └── audit.py            # Audit logging
├── persistence/             # State storage backends
│   ├── base.py             # StateStore interface
│   ├── memory.py           # In-memory (dev/test)
│   ├── redis_store.py      # Redis (distributed)
│   └── database.py         # SQLAlchemy (PostgreSQL/MySQL)
├── resilience/              # Fault tolerance
│   ├── retry.py            # Retry with exponential backoff
│   └── circuit_breaker.py  # Circuit breaker pattern
├── observability/           # Monitoring & tracing
│   ├── metrics.py          # Prometheus metrics
│   ├── tracing.py          # OpenTelemetry spans
│   └── evalai_tracer.py    # EvalAI platform integration
├── realtime/                # Real-time updates
│   ├── websocket.py        # WebSocket manager
│   └── events.py           # Event bus (pub/sub + Redis bridge)
├── validation/              # Config validation
│   ├── blueprint.py        # Blueprint validator
│   └── config.py           # Pydantic schemas
├── hitl/                    # Human-in-the-loop
│   ├── queue.py            # HITL request queue
│   ├── escalation.py       # Escalation policies
│   └── manager.py          # HITL orchestration + feedback loop
├── multitenancy/            # Multi-tenant support
│   ├── tenant.py           # Tenant model
│   ├── tenant_manager.py   # Tenant lifecycle
│   └── isolation.py        # Execution isolation
├── api/                     # FastAPI routers
│   ├── agents.py
│   ├── governance.py
│   ├── hitl.py
│   ├── tenants.py
│   └── webhooks.py         # Inbound webhooks (Zendesk/Slack/Jira)
└── sdk.py                   # Main SDK entry point
```

## Configuration

Environment variables:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | For LLM calls |
| `PINECONE_API_KEY` | No | Vector store (golden paths + KB search) |
| `PINECONE_INDEX_NAME` | No | Vector index name (default: `support-docs`) |
| `DATABASE_URL` | No | Postgres for persistence + AGE graph |
| `REDIS_URL` | No | Redis for activity stream |
| `ACTIVITY_GRAPH_NAME` | No | AGE graph name (default: `support101`) |
| `PLAYBOOK_MIN_SAMPLES` | No | Min traces to create playbook (default: `3`) |
| `PLAYBOOK_MIN_SUCCESS_RATE` | No | Min success rate to suggest (default: `0.7`) |
| `EVALAI_API_KEY` | No | EvalAI platform tracing |
| `EVALAI_BASE_URL` | No | EvalAI platform URL |
| `EVALAI_ORGANIZATION_ID` | No | EvalAI org ID |

All components gracefully degrade when their env vars are not set.

## Testing

```bash
pytest tests/agent_framework/ -v
```
