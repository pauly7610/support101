"""
Agent Executor for running agents with proper lifecycle management.

Handles:
- Async execution with timeout
- State persistence
- Audit logging
- Error recovery
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .agent_registry import AgentRegistry
from .base_agent import AgentStatus, BaseAgent


class ExecutionResult:
    """Result of an agent execution."""

    def __init__(
        self,
        agent_id: str,
        execution_id: str,
        status: AgentStatus,
        output: Dict[str, Any],
        steps: List[Dict[str, Any]],
        duration_ms: int,
        error: Optional[str] = None,
    ) -> None:
        self.agent_id = agent_id
        self.execution_id = execution_id
        self.status = status
        self.output = output
        self.steps = steps
        self.duration_ms = duration_ms
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "execution_id": self.execution_id,
            "status": self.status.value,
            "output": self.output,
            "steps_count": len(self.steps),
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class AgentExecutor:
    """
    Executes agents with proper lifecycle management.

    Features:
    - Timeout handling
    - State checkpointing
    - Audit trail generation
    - Concurrent execution limits
    """

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        max_concurrent: int = 10,
        default_timeout: int = 300,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running_executions: Dict[str, asyncio.Task] = {}
        self._audit_callback: Optional[Callable] = None

    def set_audit_callback(self, callback: Callable) -> None:
        """Set callback for audit logging."""
        self._audit_callback = callback

    async def _log_audit(
        self,
        event_type: str,
        agent_id: str,
        tenant_id: str,
        details: Dict[str, Any],
    ) -> None:
        """Log an audit event."""
        if self._audit_callback:
            event = {
                "event_type": event_type,
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details,
            }
            result = self._audit_callback(event)
            if hasattr(result, "__await__"):
                await result

    async def execute(
        self,
        agent: BaseAgent,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute an agent with the given input.

        Args:
            agent: Agent instance to execute
            input_data: Input data for the agent
            timeout: Optional timeout override

        Returns:
            ExecutionResult with output and metadata
        """
        timeout = timeout or agent.config.timeout_seconds or self.default_timeout
        start_time = datetime.utcnow()

        await self._log_audit(
            "execution_started",
            agent.agent_id,
            agent.tenant_id,
            {"input_keys": list(input_data.keys())},
        )

        async with self._semaphore:
            try:
                state = await asyncio.wait_for(
                    agent.run(input_data),
                    timeout=timeout,
                )

                await self.registry.persist_state(agent)

                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                await self._log_audit(
                    "execution_completed",
                    agent.agent_id,
                    agent.tenant_id,
                    {
                        "status": state.status.value,
                        "steps": state.current_step,
                        "duration_ms": duration_ms,
                    },
                )

                return ExecutionResult(
                    agent_id=agent.agent_id,
                    execution_id=state.execution_id,
                    status=state.status,
                    output=state.output_data,
                    steps=state.intermediate_steps,
                    duration_ms=duration_ms,
                )

            except asyncio.TimeoutError:
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                await self._log_audit(
                    "execution_timeout",
                    agent.agent_id,
                    agent.tenant_id,
                    {"timeout_seconds": timeout, "duration_ms": duration_ms},
                )

                return ExecutionResult(
                    agent_id=agent.agent_id,
                    execution_id=agent.state.execution_id if agent.state else "unknown",
                    status=AgentStatus.FAILED,
                    output={},
                    steps=agent.state.intermediate_steps if agent.state else [],
                    duration_ms=duration_ms,
                    error=f"Execution timed out after {timeout}s",
                )

            except Exception as e:
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                await self._log_audit(
                    "execution_failed",
                    agent.agent_id,
                    agent.tenant_id,
                    {"error": str(e), "duration_ms": duration_ms},
                )

                return ExecutionResult(
                    agent_id=agent.agent_id,
                    execution_id=agent.state.execution_id if agent.state else "unknown",
                    status=AgentStatus.FAILED,
                    output={},
                    steps=agent.state.intermediate_steps if agent.state else [],
                    duration_ms=duration_ms,
                    error=str(e),
                )

    async def execute_by_id(
        self,
        agent_id: str,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """Execute an agent by its ID."""
        agent = self.registry.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        return await self.execute(agent, input_data, timeout)

    async def resume(
        self,
        agent_id: str,
        human_feedback: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Resume an agent that is awaiting human feedback.

        Args:
            agent_id: ID of the agent to resume
            human_feedback: Feedback from human reviewer

        Returns:
            ExecutionResult after resumption
        """
        agent = self.registry.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")

        if not agent.state or agent.state.status != AgentStatus.AWAITING_HUMAN:
            raise RuntimeError(f"Agent '{agent_id}' is not awaiting human feedback")

        await self._log_audit(
            "human_feedback_provided",
            agent.agent_id,
            agent.tenant_id,
            {"feedback_keys": list(human_feedback.keys())},
        )

        await agent.provide_human_feedback(human_feedback)

        return await self.execute(agent, agent.state.input_data)

    def get_running_count(self) -> int:
        """Get count of currently running executions."""
        return self.max_concurrent - self._semaphore._value

    async def cancel(self, agent_id: str) -> bool:
        """Cancel a running agent execution."""
        task = self._running_executions.get(agent_id)
        if task and not task.done():
            task.cancel()

            await self._log_audit(
                "execution_cancelled",
                agent_id,
                "",
                {},
            )
            return True
        return False
