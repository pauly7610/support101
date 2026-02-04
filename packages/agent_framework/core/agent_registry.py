"""
Agent Registry for managing agent blueprints and instances.

Provides:
- Blueprint registration and discovery
- Agent instance lifecycle management
- Multi-tenant isolation
- Agent lookup and querying
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type

from .base_agent import AgentConfig, AgentStatus, BaseAgent


class AgentBlueprint:
    """
    A reusable agent template that can be instantiated multiple times.

    Blueprints define the structure and behavior of agents without
    creating actual instances.
    """

    def __init__(
        self,
        name: str,
        agent_class: Type[BaseAgent],
        description: str = "",
        default_config: Optional[Dict[str, Any]] = None,
        required_tools: Optional[List[str]] = None,
        version: str = "1.0.0",
    ) -> None:
        self.name = name
        self.agent_class = agent_class
        self.description = description
        self.default_config = default_config or {}
        self.required_tools = required_tools or []
        self.version = version
        self.created_at = datetime.utcnow()

    def create_instance(
        self,
        tenant_id: str,
        name: str,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> BaseAgent:
        """Create a new agent instance from this blueprint."""
        merged_config = {**self.default_config, **(config_overrides or {})}

        config = AgentConfig(
            tenant_id=tenant_id,
            blueprint_name=self.name,
            name=name,
            **merged_config,
        )

        return self.agent_class(config)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize blueprint metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "required_tools": self.required_tools,
            "default_config": self.default_config,
            "created_at": self.created_at.isoformat(),
        }


class AgentRegistry:
    """
    Central registry for agent blueprints and running instances.

    Supports:
    - Blueprint registration and discovery
    - Instance creation with tenant isolation
    - Active agent tracking
    - Agent state persistence hooks
    """

    _instance: Optional["AgentRegistry"] = None

    def __new__(cls) -> "AgentRegistry":
        """Singleton pattern for global registry access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._blueprints: Dict[str, AgentBlueprint] = {}
        self._agents: Dict[str, BaseAgent] = {}  # agent_id -> agent
        self._tenant_agents: Dict[str, List[str]] = {}  # tenant_id -> [agent_ids]
        self._state_persistence_hook: Optional[Callable] = None
        self._initialized = True

    def register_blueprint(self, blueprint: AgentBlueprint) -> None:
        """Register a new agent blueprint."""
        if blueprint.name in self._blueprints:
            raise ValueError(f"Blueprint '{blueprint.name}' already registered")
        self._blueprints[blueprint.name] = blueprint

    def get_blueprint(self, name: str) -> Optional[AgentBlueprint]:
        """Get a blueprint by name."""
        return self._blueprints.get(name)

    def list_blueprints(self) -> List[Dict[str, Any]]:
        """List all registered blueprints."""
        return [bp.to_dict() for bp in self._blueprints.values()]

    def create_agent(
        self,
        blueprint_name: str,
        tenant_id: str,
        agent_name: str,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> BaseAgent:
        """
        Create a new agent instance from a blueprint.

        Args:
            blueprint_name: Name of the blueprint to use
            tenant_id: Tenant ID for isolation
            agent_name: Human-readable name for the agent
            config_overrides: Optional config overrides

        Returns:
            New agent instance
        """
        blueprint = self._blueprints.get(blueprint_name)
        if not blueprint:
            raise ValueError(f"Blueprint '{blueprint_name}' not found")

        agent = blueprint.create_instance(tenant_id, agent_name, config_overrides)

        self._agents[agent.agent_id] = agent

        if tenant_id not in self._tenant_agents:
            self._tenant_agents[tenant_id] = []
        self._tenant_agents[tenant_id].append(agent.agent_id)

        return agent

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def get_tenant_agents(self, tenant_id: str) -> List[BaseAgent]:
        """Get all agents for a tenant."""
        agent_ids = self._tenant_agents.get(tenant_id, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def list_agents(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        blueprint_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List agents with optional filters.

        Args:
            tenant_id: Filter by tenant
            status: Filter by status
            blueprint_name: Filter by blueprint

        Returns:
            List of agent summaries
        """
        agents = self._agents.values()

        if tenant_id:
            agents = [a for a in agents if a.tenant_id == tenant_id]

        if blueprint_name:
            agents = [a for a in agents if a.config.blueprint_name == blueprint_name]

        if status:
            agents = [a for a in agents if a.state and a.state.status == status]

        return [
            {
                "agent_id": a.agent_id,
                "tenant_id": a.tenant_id,
                "name": a.config.name,
                "blueprint": a.config.blueprint_name,
                "status": a.state.status.value if a.state else "not_started",
                "created_at": a.config.created_at.isoformat(),
            }
            for a in agents
        ]

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the registry."""
        agent = self._agents.pop(agent_id, None)
        if agent:
            tenant_agents = self._tenant_agents.get(agent.tenant_id, [])
            if agent_id in tenant_agents:
                tenant_agents.remove(agent_id)
            return True
        return False

    def set_state_persistence_hook(self, hook: Callable) -> None:
        """Set a callback for persisting agent state changes."""
        self._state_persistence_hook = hook

    async def persist_state(self, agent: BaseAgent) -> None:
        """Persist agent state using the registered hook."""
        if self._state_persistence_hook and agent.state:
            result = self._state_persistence_hook(agent.agent_id, agent.state)
            if hasattr(result, "__await__"):
                await result

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        status_counts: Dict[str, int] = {}
        for agent in self._agents.values():
            status = agent.state.status.value if agent.state else "not_started"
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_blueprints": len(self._blueprints),
            "total_agents": len(self._agents),
            "total_tenants": len(self._tenant_agents),
            "agents_by_status": status_counts,
        }

    def reset(self) -> None:
        """Reset the registry (for testing)."""
        self._blueprints.clear()
        self._agents.clear()
        self._tenant_agents.clear()
