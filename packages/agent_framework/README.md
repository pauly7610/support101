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

## Architecture

```
packages/agent_framework/
├── core/                    # Core agent infrastructure
│   ├── base_agent.py       # BaseAgent abstract class
│   ├── agent_registry.py   # Blueprint & instance registry
│   └── agent_executor.py   # Execution with lifecycle management
├── templates/               # Agent blueprints
│   ├── support_agent.py    # RAG-powered support agent
│   └── triage_agent.py     # Ticket routing agent
├── governance/              # Permissions & audit
│   ├── permissions.py      # RBAC system
│   └── audit.py            # Audit logging
├── hitl/                    # Human-in-the-loop
│   ├── queue.py            # HITL request queue
│   ├── escalation.py       # Escalation policies
│   └── manager.py          # HITL orchestration
├── multitenancy/            # Multi-tenant support
│   ├── tenant.py           # Tenant model
│   ├── tenant_manager.py   # Tenant lifecycle
│   └── isolation.py        # Execution isolation
├── api/                     # FastAPI routers
│   ├── agents.py
│   ├── governance.py
│   ├── hitl.py
│   └── tenants.py
└── sdk.py                   # Main SDK entry point
```

## Configuration

Environment variables:
- `OPENAI_API_KEY` - For LLM calls
- `PINECONE_API_KEY` - For vector store
- `PINECONE_INDEX_NAME` - Vector index name

## Testing

```bash
pytest tests/agent_framework/ -v
```
