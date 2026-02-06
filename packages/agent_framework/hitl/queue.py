"""
Human-in-the-Loop Queue System.

Manages requests that require human review, approval, or feedback.
Supports priority-based queuing, SLA tracking, and assignment.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4


class HITLRequestType(StrEnum):
    """Types of HITL requests."""

    APPROVAL = "approval"
    REVIEW = "review"
    FEEDBACK = "feedback"
    ESCALATION = "escalation"
    OVERRIDE = "override"
    CLARIFICATION = "clarification"


class HITLRequestStatus(StrEnum):
    """Status of HITL requests."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class HITLPriority(StrEnum):
    """Priority levels for HITL requests."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class HITLRequest:
    """A request for human intervention."""

    request_id: str = field(default_factory=lambda: str(uuid4()))
    request_type: HITLRequestType = HITLRequestType.REVIEW
    priority: HITLPriority = HITLPriority.MEDIUM
    status: HITLRequestStatus = HITLRequestStatus.PENDING

    agent_id: str = ""
    tenant_id: str = ""
    execution_id: str = ""

    title: str = ""
    description: str = ""
    question: str | None = None
    options: list[str] = field(default_factory=list)

    context: dict[str, Any] = field(default_factory=dict)
    agent_state_snapshot: dict[str, Any] = field(default_factory=dict)

    assigned_to: str | None = None
    assigned_at: datetime | None = None

    response: dict[str, Any] | None = None
    responded_by: str | None = None
    responded_at: datetime | None = None

    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    sla_deadline: datetime | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if request has expired."""
        return bool(self.expires_at and datetime.utcnow() > self.expires_at)

    def is_sla_breached(self) -> bool:
        """Check if SLA has been breached."""
        return bool(self.sla_deadline and datetime.utcnow() > self.sla_deadline)

    def time_in_queue(self) -> timedelta:
        """Get time spent in queue."""
        end_time = self.responded_at or datetime.utcnow()
        return end_time - self.created_at

    def to_dict(self) -> dict[str, Any]:
        """Serialize request."""
        return {
            "request_id": self.request_id,
            "request_type": self.request_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "execution_id": self.execution_id,
            "title": self.title,
            "description": self.description,
            "question": self.question,
            "options": self.options,
            "assigned_to": self.assigned_to,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "response": self.response,
            "responded_by": self.responded_by,
            "responded_at": (self.responded_at.isoformat() if self.responded_at else None),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "sla_deadline": (self.sla_deadline.isoformat() if self.sla_deadline else None),
            "is_expired": self.is_expired(),
            "is_sla_breached": self.is_sla_breached(),
            "time_in_queue_seconds": self.time_in_queue().total_seconds(),
            "metadata": self.metadata,
        }


class HITLQueue:
    """
    Priority queue for human-in-the-loop requests.

    Features:
    - Priority-based ordering
    - SLA tracking and alerts
    - Assignment management
    - Tenant isolation
    - Expiration handling
    """

    SLA_DEFAULTS = {
        HITLPriority.CRITICAL: timedelta(minutes=5),
        HITLPriority.HIGH: timedelta(minutes=15),
        HITLPriority.MEDIUM: timedelta(hours=1),
        HITLPriority.LOW: timedelta(hours=4),
    }

    def __init__(self) -> None:
        self._requests: dict[str, HITLRequest] = {}
        self._tenant_queues: dict[str, list[str]] = {}
        self._user_assignments: dict[str, list[str]] = {}
        self._on_request_callbacks: list[Callable] = []
        self._on_sla_breach_callbacks: list[Callable] = []
        self._sla_check_task: asyncio.Task | None = None

    def on_request(self, callback: Callable) -> None:
        """Register callback for new requests."""
        self._on_request_callbacks.append(callback)

    def on_sla_breach(self, callback: Callable) -> None:
        """Register callback for SLA breaches."""
        self._on_sla_breach_callbacks.append(callback)

    async def _notify_new_request(self, request: HITLRequest) -> None:
        """Notify callbacks of new request."""
        for callback in self._on_request_callbacks:
            try:
                result = callback(request)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"HITL callback error: {e}")

    async def _notify_sla_breach(self, request: HITLRequest) -> None:
        """Notify callbacks of SLA breach."""
        for callback in self._on_sla_breach_callbacks:
            try:
                result = callback(request)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"SLA breach callback error: {e}")

    async def enqueue(
        self,
        request_type: HITLRequestType,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
        title: str,
        description: str,
        priority: HITLPriority = HITLPriority.MEDIUM,
        question: str | None = None,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        agent_state: dict[str, Any] | None = None,
        expires_in: timedelta | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HITLRequest:
        """
        Add a new request to the queue.

        Args:
            request_type: Type of HITL request
            agent_id: ID of the requesting agent
            tenant_id: Tenant for isolation
            execution_id: Current execution ID
            title: Short title for the request
            description: Detailed description
            priority: Request priority
            question: Optional question for the reviewer
            options: Optional response options
            context: Additional context data
            agent_state: Snapshot of agent state
            expires_in: Optional expiration duration
            metadata: Additional metadata

        Returns:
            Created HITLRequest
        """
        now = datetime.utcnow()

        sla_deadline = now + self.SLA_DEFAULTS.get(priority, timedelta(hours=1))

        expires_at = None
        if expires_in:
            expires_at = now + expires_in

        request = HITLRequest(
            request_type=request_type,
            priority=priority,
            agent_id=agent_id,
            tenant_id=tenant_id,
            execution_id=execution_id,
            title=title,
            description=description,
            question=question,
            options=options or [],
            context=context or {},
            agent_state_snapshot=agent_state or {},
            sla_deadline=sla_deadline,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        self._requests[request.request_id] = request

        if tenant_id not in self._tenant_queues:
            self._tenant_queues[tenant_id] = []
        self._tenant_queues[tenant_id].append(request.request_id)

        await self._notify_new_request(request)

        return request

    def get_request(self, request_id: str) -> HITLRequest | None:
        """Get a request by ID."""
        return self._requests.get(request_id)

    def get_pending(
        self,
        tenant_id: str | None = None,
        priority: HITLPriority | None = None,
        request_type: HITLRequestType | None = None,
        limit: int = 50,
    ) -> list[HITLRequest]:
        """
        Get pending requests with optional filters.

        Returns requests sorted by priority and creation time.
        """
        requests = [
            r
            for r in self._requests.values()
            if r.status == HITLRequestStatus.PENDING and not r.is_expired()
        ]

        if tenant_id:
            requests = [r for r in requests if r.tenant_id == tenant_id]

        if priority:
            requests = [r for r in requests if r.priority == priority]

        if request_type:
            requests = [r for r in requests if r.request_type == request_type]

        priority_order = {
            HITLPriority.CRITICAL: 0,
            HITLPriority.HIGH: 1,
            HITLPriority.MEDIUM: 2,
            HITLPriority.LOW: 3,
        }

        requests.sort(key=lambda r: (priority_order[r.priority], r.created_at))

        return requests[:limit]

    def assign(
        self,
        request_id: str,
        user_id: str,
    ) -> bool:
        """Assign a request to a user."""
        request = self._requests.get(request_id)
        if not request:
            return False

        if request.status != HITLRequestStatus.PENDING:
            return False

        request.assigned_to = user_id
        request.assigned_at = datetime.utcnow()
        request.status = HITLRequestStatus.ASSIGNED

        if user_id not in self._user_assignments:
            self._user_assignments[user_id] = []
        self._user_assignments[user_id].append(request_id)

        return True

    def unassign(self, request_id: str) -> bool:
        """Unassign a request."""
        request = self._requests.get(request_id)
        if not request:
            return False

        if request.assigned_to:
            user_assignments = self._user_assignments.get(request.assigned_to, [])
            if request_id in user_assignments:
                user_assignments.remove(request_id)

        request.assigned_to = None
        request.assigned_at = None
        request.status = HITLRequestStatus.PENDING

        return True

    async def respond(
        self,
        request_id: str,
        response: dict[str, Any],
        user_id: str,
    ) -> bool:
        """
        Provide a response to a request.

        Args:
            request_id: ID of the request
            response: Response data
            user_id: ID of the responding user

        Returns:
            True if successful
        """
        request = self._requests.get(request_id)
        if not request:
            return False

        if request.status not in [
            HITLRequestStatus.PENDING,
            HITLRequestStatus.ASSIGNED,
        ]:
            return False

        request.response = response
        request.responded_by = user_id
        request.responded_at = datetime.utcnow()
        request.status = HITLRequestStatus.COMPLETED

        return True

    def cancel(self, request_id: str, reason: str = "") -> bool:
        """Cancel a request."""
        request = self._requests.get(request_id)
        if not request:
            return False

        request.status = HITLRequestStatus.CANCELLED
        request.metadata["cancellation_reason"] = reason

        return True

    def get_user_assignments(self, user_id: str) -> list[HITLRequest]:
        """Get all requests assigned to a user."""
        request_ids = self._user_assignments.get(user_id, [])
        return [
            self._requests[rid]
            for rid in request_ids
            if rid in self._requests and self._requests[rid].status == HITLRequestStatus.ASSIGNED
        ]

    def get_queue_stats(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Get queue statistics."""
        requests = list(self._requests.values())
        if tenant_id:
            requests = [r for r in requests if r.tenant_id == tenant_id]

        pending = [r for r in requests if r.status == HITLRequestStatus.PENDING]
        assigned = [r for r in requests if r.status == HITLRequestStatus.ASSIGNED]
        completed = [r for r in requests if r.status == HITLRequestStatus.COMPLETED]
        sla_breached = [r for r in pending + assigned if r.is_sla_breached()]

        avg_response_time = None
        if completed:
            total_time = sum(r.time_in_queue().total_seconds() for r in completed)
            avg_response_time = total_time / len(completed)

        priority_counts = {}
        for p in HITLPriority:
            priority_counts[p.value] = len([r for r in pending if r.priority == p])

        return {
            "total_requests": len(requests),
            "pending": len(pending),
            "assigned": len(assigned),
            "completed": len(completed),
            "sla_breached": len(sla_breached),
            "by_priority": priority_counts,
            "avg_response_time_seconds": avg_response_time,
        }

    async def check_expirations(self) -> list[HITLRequest]:
        """Check and update expired requests."""
        expired = []
        for request in self._requests.values():
            if (
                request.status
                in [
                    HITLRequestStatus.PENDING,
                    HITLRequestStatus.ASSIGNED,
                ]
                and request.is_expired()
            ):
                request.status = HITLRequestStatus.EXPIRED
                expired.append(request)
        return expired

    async def check_sla_breaches(self) -> list[HITLRequest]:
        """Check for SLA breaches and notify."""
        breached = []
        for request in self._requests.values():
            if (
                request.status
                in [
                    HITLRequestStatus.PENDING,
                    HITLRequestStatus.ASSIGNED,
                ]
                and request.is_sla_breached()
                and "sla_notified" not in request.metadata
            ):
                request.metadata["sla_notified"] = True
                breached.append(request)
                await self._notify_sla_breach(request)
        return breached

    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start background monitoring for expirations and SLA breaches."""

        async def monitor_loop():
            while True:
                await asyncio.sleep(interval_seconds)
                await self.check_expirations()
                await self.check_sla_breaches()

        self._sla_check_task = asyncio.create_task(monitor_loop())

    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if self._sla_check_task:
            self._sla_check_task.cancel()
            self._sla_check_task = None
