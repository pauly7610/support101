"""
Base Agent class for the Enterprise Agent Framework.

All agent blueprints inherit from BaseAgent, which provides:
- State management
- Tool registration
- Human-in-the-loop hooks
- Audit logging integration
- Multi-tenant isolation
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentStatus(StrEnum):
    """Agent lifecycle status."""

    IDLE = "idle"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentConfig(BaseModel):
    """Configuration for an agent instance."""

    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    blueprint_name: str
    name: str
    description: str | None = None
    max_iterations: int = 10
    timeout_seconds: int = 300
    require_human_approval: bool = False
    confidence_threshold: float = 0.75
    allowed_tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """Runtime state of an agent execution."""

    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    tenant_id: str
    status: AgentStatus = AgentStatus.IDLE
    current_step: int = 0
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    intermediate_steps: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    human_feedback_request: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass
class Tool:
    """Tool definition for agent use."""

    name: str
    description: str
    func: Callable
    requires_approval: bool = False
    allowed_tenants: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the framework.

    Subclasses must implement:
    - plan(): Determine next action based on current state
    - execute_step(): Execute a single step of the agent's workflow
    - should_continue(): Determine if agent should continue or stop
    """

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.state: AgentState | None = None
        self._tools: dict[str, Tool] = {}
        self._hooks: dict[str, list[Callable]] = {
            "pre_step": [],
            "post_step": [],
            "on_error": [],
            "on_human_request": [],
            "on_complete": [],
        }

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @property
    def tenant_id(self) -> str:
        return self.config.tenant_id

    def register_tool(self, tool: Tool) -> None:
        """Register a tool for this agent to use."""
        if self.config.allowed_tools and tool.name not in self.config.allowed_tools:
            raise PermissionError(
                f"Tool '{tool.name}' not in allowed tools for agent '{self.agent_id}'"
            )
        self._tools[tool.name] = tool

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """Register a lifecycle hook callback."""
        if hook_name not in self._hooks:
            raise ValueError(f"Unknown hook: {hook_name}")
        self._hooks[hook_name].append(callback)

    async def _run_hooks(self, hook_name: str, **kwargs: Any) -> None:
        """Execute all registered hooks for a given event."""
        for callback in self._hooks.get(hook_name, []):
            if callable(callback):
                result = callback(self, **kwargs)
                if hasattr(result, "__await__"):
                    await result

    def initialize_state(self, input_data: dict[str, Any]) -> AgentState:
        """Initialize a new execution state."""
        self.state = AgentState(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            input_data=input_data,
            started_at=datetime.utcnow(),
        )
        return self.state

    @abstractmethod
    async def plan(self, state: AgentState) -> dict[str, Any]:
        """
        Determine the next action based on current state.

        Returns:
            Dict containing 'action' and 'action_input' keys.
        """

    @abstractmethod
    async def execute_step(self, state: AgentState, action: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a single step of the agent's workflow.

        Args:
            state: Current agent state
            action: Action to execute (from plan())

        Returns:
            Step result to be added to intermediate_steps.
        """

    @abstractmethod
    def should_continue(self, state: AgentState) -> bool:
        """Determine if the agent should continue execution."""

    async def request_human_feedback(
        self,
        question: str,
        context: dict[str, Any],
        options: list[str] | None = None,
    ) -> None:
        """
        Request human-in-the-loop feedback.

        Pauses agent execution until human provides feedback.
        """
        if self.state is None:
            raise RuntimeError("Agent state not initialized")

        self.state.status = AgentStatus.AWAITING_HUMAN
        self.state.human_feedback_request = {
            "question": question,
            "context": context,
            "options": options,
            "requested_at": datetime.utcnow().isoformat(),
        }
        await self._run_hooks("on_human_request", request=self.state.human_feedback_request)

    async def provide_human_feedback(self, feedback: dict[str, Any]) -> None:
        """Provide human feedback to resume agent execution."""
        if self.state is None:
            raise RuntimeError("Agent state not initialized")

        if self.state.status != AgentStatus.AWAITING_HUMAN:
            raise RuntimeError("Agent is not awaiting human feedback")

        self.state.intermediate_steps.append({
            "type": "human_feedback",
            "feedback": feedback,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.state.human_feedback_request = None
        self.state.status = AgentStatus.RUNNING

    async def run(self, input_data: dict[str, Any]) -> AgentState:
        """
        Execute the agent's full workflow.

        Args:
            input_data: Initial input for the agent

        Returns:
            Final agent state after execution.
        """
        self.initialize_state(input_data)
        assert self.state is not None

        self.state.status = AgentStatus.RUNNING

        try:
            while self.should_continue(self.state):
                if self.state.status == AgentStatus.AWAITING_HUMAN:
                    break

                await self._run_hooks("pre_step", state=self.state)

                action = await self.plan(self.state)

                if self.config.require_human_approval and action.get("requires_approval"):
                    await self.request_human_feedback(
                        question=f"Approve action: {action.get('action')}?",
                        context=action,
                        options=["approve", "reject", "modify"],
                    )
                    break

                step_result = await self.execute_step(self.state, action)
                self.state.intermediate_steps.append(step_result)
                self.state.current_step += 1

                await self._run_hooks("post_step", state=self.state, result=step_result)

            if self.state.status == AgentStatus.RUNNING:
                self.state.status = AgentStatus.COMPLETED
                self.state.completed_at = datetime.utcnow()
                await self._run_hooks("on_complete", state=self.state)

        except Exception as e:
            self.state.status = AgentStatus.FAILED
            self.state.error = str(e)
            self.state.completed_at = datetime.utcnow()
            await self._run_hooks("on_error", state=self.state, error=e)
            raise

        return self.state

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent configuration and state."""
        return {
            "config": self.config.model_dump(),
            "state": self.state.model_dump() if self.state else None,
            "tools": list(self._tools.keys()),
        }
