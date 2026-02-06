"""
HITL Manager - Orchestrates human-in-the-loop workflows.

Provides a unified interface for:
- Managing HITL requests
- Coordinating with agents
- Tracking reviewer workloads
- Analytics and reporting
"""

import logging
from datetime import datetime
from typing import Any

from ..core.agent_registry import AgentRegistry
from ..core.base_agent import AgentStatus, BaseAgent
from ..governance.audit import AuditEventType, AuditLogger
from .escalation import EscalationLevel, EscalationManager
from .queue import HITLPriority, HITLQueue, HITLRequest, HITLRequestType

logger = logging.getLogger(__name__)


class HITLManager:
    """
    Central manager for Human-in-the-Loop operations.

    Coordinates between:
    - HITL Queue (request management)
    - Agent Registry (agent state)
    - Escalation Manager (escalation policies)
    - Audit Logger (compliance)
    - Feedback Collector (continuous learning)
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        audit_logger: AuditLogger | None = None,
        feedback_collector: Any | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.audit_logger = audit_logger or AuditLogger()
        self.feedback_collector = feedback_collector
        self.queue = HITLQueue()
        self.escalation_manager = EscalationManager(self.queue)

        self._reviewers: dict[str, dict[str, Any]] = {}
        self._reviewer_workloads: dict[str, int] = {}
        self._max_workload_per_reviewer: int = 10

        self._setup_callbacks()

    def _setup_callbacks(self) -> None:
        """Set up internal callbacks."""
        self.queue.on_request(self._on_new_request)
        self.queue.on_sla_breach(self._on_sla_breach)

    async def _on_new_request(self, request: HITLRequest) -> None:
        """Handle new HITL request."""
        await self.audit_logger.log_agent_event(
            event_type=AuditEventType.HUMAN_FEEDBACK_REQUESTED,
            agent_id=request.agent_id,
            tenant_id=request.tenant_id,
            details={
                "request_id": request.request_id,
                "request_type": request.request_type.value,
                "priority": request.priority.value,
            },
        )

        if request.priority in [HITLPriority.CRITICAL, HITLPriority.HIGH]:
            await self._auto_assign(request)

    async def _on_sla_breach(self, request: HITLRequest) -> None:
        """Handle SLA breach."""
        await self.audit_logger.log_security_event(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            agent_id=request.agent_id,
            tenant_id=request.tenant_id,
            resource="hitl_sla",
            action="sla_breach",
            outcome="breached",
            details={
                "request_id": request.request_id,
                "sla_deadline": (
                    request.sla_deadline.isoformat() if request.sla_deadline else None
                ),
                "time_in_queue_seconds": request.time_in_queue().total_seconds(),
            },
        )

    async def _auto_assign(self, request: HITLRequest) -> bool:
        """Attempt to auto-assign request to available reviewer."""
        available_reviewers = [
            (rid, info)
            for rid, info in self._reviewers.items()
            if info.get("tenant_id") == request.tenant_id
            and self._reviewer_workloads.get(rid, 0) < self._max_workload_per_reviewer
            and info.get("available", True)
        ]

        if not available_reviewers:
            return False

        available_reviewers.sort(key=lambda x: self._reviewer_workloads.get(x[0], 0))
        reviewer_id = available_reviewers[0][0]

        return self.queue.assign(request.request_id, reviewer_id)

    def register_reviewer(
        self,
        reviewer_id: str,
        tenant_id: str,
        name: str,
        skills: list[str] | None = None,
        max_workload: int | None = None,
    ) -> None:
        """Register a human reviewer."""
        self._reviewers[reviewer_id] = {
            "tenant_id": tenant_id,
            "name": name,
            "skills": skills or [],
            "available": True,
            "registered_at": datetime.utcnow(),
        }
        self._reviewer_workloads[reviewer_id] = 0

        if max_workload:
            self._max_workload_per_reviewer = max_workload

    def set_reviewer_availability(self, reviewer_id: str, available: bool) -> bool:
        """Set reviewer availability status."""
        if reviewer_id in self._reviewers:
            self._reviewers[reviewer_id]["available"] = available
            return True
        return False

    async def request_approval(
        self,
        agent: BaseAgent,
        action: str,
        context: dict[str, Any],
        options: list[str] | None = None,
    ) -> HITLRequest:
        """
        Request human approval for an agent action.

        Args:
            agent: The agent requesting approval
            action: Description of the action
            context: Context for the decision
            options: Response options (default: approve/reject)

        Returns:
            Created HITL request
        """
        if not agent.state:
            raise RuntimeError("Agent state not initialized")

        request = await self.queue.enqueue(
            request_type=HITLRequestType.APPROVAL,
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            execution_id=agent.state.execution_id,
            title=f"Approval Required: {action}",
            description=f"Agent '{agent.config.name}' requests approval for: {action}",
            priority=(
                HITLPriority.HIGH if agent.config.require_human_approval else HITLPriority.MEDIUM
            ),
            question=f"Do you approve this action: {action}?",
            options=options or ["approve", "reject", "modify"],
            context=context,
            agent_state=agent.state.model_dump(),
        )

        agent.state.status = AgentStatus.AWAITING_HUMAN
        agent.state.human_feedback_request = {
            "hitl_request_id": request.request_id,
            "action": action,
            "requested_at": datetime.utcnow().isoformat(),
        }

        return request

    async def request_feedback(
        self,
        agent: BaseAgent,
        question: str,
        context: dict[str, Any],
        options: list[str] | None = None,
    ) -> HITLRequest:
        """Request human feedback/clarification."""
        if not agent.state:
            raise RuntimeError("Agent state not initialized")

        request = await self.queue.enqueue(
            request_type=HITLRequestType.FEEDBACK,
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            execution_id=agent.state.execution_id,
            title="Feedback Requested",
            description=question,
            priority=HITLPriority.MEDIUM,
            question=question,
            options=options,
            context=context,
            agent_state=agent.state.model_dump(),
        )

        agent.state.status = AgentStatus.AWAITING_HUMAN
        agent.state.human_feedback_request = {
            "hitl_request_id": request.request_id,
            "question": question,
            "requested_at": datetime.utcnow().isoformat(),
        }

        return request

    async def request_review(
        self,
        agent: BaseAgent,
        content: str,
        context: dict[str, Any],
    ) -> HITLRequest:
        """Request human review of agent output."""
        if not agent.state:
            raise RuntimeError("Agent state not initialized")

        request = await self.queue.enqueue(
            request_type=HITLRequestType.REVIEW,
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            execution_id=agent.state.execution_id,
            title="Review Required",
            description=f"Please review the following agent output:\n\n{content}",
            priority=HITLPriority.MEDIUM,
            question="Is this response appropriate?",
            options=["approve", "edit", "reject"],
            context=context,
            agent_state=agent.state.model_dump(),
        )

        return request

    async def provide_response(
        self,
        request_id: str,
        response: dict[str, Any],
        reviewer_id: str,
    ) -> bool:
        """
        Provide a response to a HITL request and resume agent.

        Args:
            request_id: ID of the request
            response: Response data
            reviewer_id: ID of the responding reviewer

        Returns:
            True if successful
        """
        request = self.queue.get_request(request_id)
        if not request:
            return False

        success = await self.queue.respond(request_id, response, reviewer_id)
        if not success:
            return False

        if reviewer_id in self._reviewer_workloads:
            self._reviewer_workloads[reviewer_id] = max(
                0, self._reviewer_workloads[reviewer_id] - 1
            )

        event_type = AuditEventType.HUMAN_FEEDBACK_PROVIDED
        if request.request_type == HITLRequestType.APPROVAL:
            if response.get("decision") == "approve":
                event_type = AuditEventType.HUMAN_APPROVAL_GRANTED
            else:
                event_type = AuditEventType.HUMAN_APPROVAL_DENIED

        await self.audit_logger.log_human_interaction(
            event_type=event_type,
            agent_id=request.agent_id,
            tenant_id=request.tenant_id,
            user_id=reviewer_id,
            execution_id=request.execution_id,
            action=request.request_type.value,
            outcome=response.get("decision", "provided"),
            details={
                "request_id": request_id,
                "response_time_seconds": request.time_in_queue().total_seconds(),
            },
        )

        # Feed outcome to continuous learning system
        if self.feedback_collector is not None:
            try:
                await self._send_to_feedback_collector(
                    request=request, response=response, reviewer_id=reviewer_id
                )
            except Exception as e:
                logger.debug("FeedbackCollector call failed: %s", e)

        agent = self.registry.get_agent(request.agent_id)
        if agent and agent.state and agent.state.status == AgentStatus.AWAITING_HUMAN:
            await agent.provide_human_feedback(response)

        return True

    async def _send_to_feedback_collector(
        self,
        request: HITLRequest,
        response: dict[str, Any],
        reviewer_id: str,
    ) -> None:
        """Route HITL outcome to the FeedbackCollector for learning."""
        trace = {
            "input_query": request.context.get("input_data", {}).get("query", ""),
            "steps": [
                s.get("action", "")
                for s in request.agent_state_snapshot.get("intermediate_steps", [])
            ],
            "output": request.context.get("output_data", {}),
            "agent_blueprint": request.metadata.get("blueprint", ""),
            "category": request.metadata.get("category", "general"),
            "articles_used": request.context.get("sources", []),
            "confidence": request.context.get("confidence", 0.0),
        }

        decision = response.get("decision", "")
        if decision == "approve":
            await self.feedback_collector.record_success(
                trace=trace, approved_by=reviewer_id, tenant_id=request.tenant_id
            )
        elif decision == "reject":
            await self.feedback_collector.record_failure(
                trace=trace,
                reason=response.get("reason", ""),
                tenant_id=request.tenant_id,
            )
        elif decision in ("modify", "edit"):
            await self.feedback_collector.record_correction(
                original_trace=trace,
                corrected_output=response.get("edited_response", response.get("response", "")),
                corrected_by=reviewer_id,
                tenant_id=request.tenant_id,
            )

    async def escalate(
        self,
        agent: BaseAgent,
        reason: str,
        level: EscalationLevel = EscalationLevel.L2,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Manually escalate an agent's current task."""
        if not agent.state:
            raise RuntimeError("Agent state not initialized")

        return await self.escalation_manager.manual_escalate(
            agent_id=agent.agent_id,
            tenant_id=agent.tenant_id,
            execution_id=agent.state.execution_id,
            reason=reason,
            level=level,
            context=context,
        )

    def get_pending_requests(
        self,
        tenant_id: str | None = None,
        reviewer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get pending HITL requests."""
        if reviewer_id:
            requests = self.queue.get_user_assignments(reviewer_id)
        else:
            requests = self.queue.get_pending(tenant_id=tenant_id)

        return [r.to_dict() for r in requests]

    def get_reviewer_dashboard(self, reviewer_id: str) -> dict[str, Any]:
        """Get dashboard data for a reviewer."""
        reviewer = self._reviewers.get(reviewer_id)
        if not reviewer:
            return {"error": "Reviewer not found"}

        assignments = self.queue.get_user_assignments(reviewer_id)
        tenant_id = reviewer.get("tenant_id")
        pending = self.queue.get_pending(tenant_id=tenant_id, limit=20)

        return {
            "reviewer": {
                "id": reviewer_id,
                "name": reviewer.get("name"),
                "available": reviewer.get("available"),
                "current_workload": self._reviewer_workloads.get(reviewer_id, 0),
                "max_workload": self._max_workload_per_reviewer,
            },
            "assignments": [a.to_dict() for a in assignments],
            "pending_in_queue": [p.to_dict() for p in pending if p.assigned_to != reviewer_id],
            "queue_stats": self.queue.get_queue_stats(tenant_id),
        }

    def get_stats(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Get comprehensive HITL statistics."""
        queue_stats = self.queue.get_queue_stats(tenant_id)
        escalation_stats = self.escalation_manager.get_escalation_stats(tenant_id)

        reviewers = self._reviewers
        if tenant_id:
            reviewers = {
                rid: info for rid, info in reviewers.items() if info.get("tenant_id") == tenant_id
            }

        available_reviewers = sum(1 for r in reviewers.values() if r.get("available"))

        return {
            "queue": queue_stats,
            "escalations": escalation_stats,
            "reviewers": {
                "total": len(reviewers),
                "available": available_reviewers,
                "total_workload": sum(self._reviewer_workloads.get(rid, 0) for rid in reviewers),
            },
        }

    async def start(self) -> None:
        """Start the HITL manager background tasks."""
        await self.queue.start_monitoring(interval_seconds=30)

    def stop(self) -> None:
        """Stop the HITL manager."""
        self.queue.stop_monitoring()
