"""
Audit Logger for Agent Framework.

Provides comprehensive audit trails for:
- Agent lifecycle events
- Execution history
- Permission changes
- Human-in-the-loop decisions
- Compliance reporting
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Optional
from uuid import uuid4


class AuditEventType(StrEnum):
    """Types of audit events."""

    AGENT_CREATED = "agent_created"
    AGENT_DELETED = "agent_deleted"
    AGENT_UPDATED = "agent_updated"

    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_TIMEOUT = "execution_timeout"
    EXECUTION_CANCELLED = "execution_cancelled"

    STEP_EXECUTED = "step_executed"
    TOOL_INVOKED = "tool_invoked"

    HUMAN_FEEDBACK_REQUESTED = "human_feedback_requested"
    HUMAN_FEEDBACK_PROVIDED = "human_feedback_provided"
    HUMAN_APPROVAL_GRANTED = "human_approval_granted"
    HUMAN_APPROVAL_DENIED = "human_approval_denied"

    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    ESCALATION_TRIGGERED = "escalation_triggered"
    ESCALATION_RESOLVED = "escalation_resolved"

    DATA_ACCESSED = "data_accessed"
    DATA_MODIFIED = "data_modified"

    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


@dataclass
class AuditEvent:
    """A single audit event."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType = AuditEventType.AGENT_CREATED
    timestamp: datetime = field(default_factory=datetime.utcnow)

    agent_id: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    execution_id: str | None = None

    resource: str | None = None
    action: str | None = None
    outcome: str | None = None

    details: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    ip_address: str | None = None
    user_agent: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize event for storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "execution_id": self.execution_id,
            "resource": self.resource,
            "action": self.action,
            "outcome": self.outcome,
            "details": self.details,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


class AuditLogger:
    """
    Centralized audit logging for the agent framework.

    Features:
    - Async event logging
    - Multiple storage backends (in-memory, database, external)
    - Event filtering and querying
    - Retention policies
    - Export capabilities
    """

    _instance: Optional["AuditLogger"] = None

    def __new__(cls) -> "AuditLogger":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._events: list[AuditEvent] = []
        self._max_events: int = 10000
        self._storage_backends: list[Callable[[AuditEvent], Any]] = []
        self._event_handlers: dict[AuditEventType, list[Callable]] = {}
        self._retention_days: int = 90
        self._initialized = True

    def add_storage_backend(self, backend: Callable[[AuditEvent], Any]) -> None:
        """Add a storage backend for audit events."""
        self._storage_backends.append(backend)

    def register_handler(
        self,
        event_type: AuditEventType,
        handler: Callable[[AuditEvent], Any],
    ) -> None:
        """Register a handler for specific event types."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def log(self, event: AuditEvent) -> str:
        """
        Log an audit event.

        Args:
            event: The audit event to log

        Returns:
            Event ID
        """
        self._events.append(event)

        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events :]

        for backend in self._storage_backends:
            try:
                result = backend(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"Audit storage backend error: {e}")

        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"Audit handler error: {e}")

        return event.event_id

    async def log_agent_event(
        self,
        event_type: AuditEventType,
        agent_id: str,
        tenant_id: str,
        details: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> str:
        """Convenience method for logging agent-related events."""
        event = AuditEvent(
            event_type=event_type,
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_id=user_id,
            details=details or {},
        )
        return await self.log(event)

    async def log_execution_event(
        self,
        event_type: AuditEventType,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Convenience method for logging execution events."""
        event = AuditEvent(
            event_type=event_type,
            agent_id=agent_id,
            tenant_id=tenant_id,
            execution_id=execution_id,
            details=details or {},
        )
        return await self.log(event)

    async def log_human_interaction(
        self,
        event_type: AuditEventType,
        agent_id: str,
        tenant_id: str,
        user_id: str,
        execution_id: str,
        action: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Log human-in-the-loop interactions."""
        event = AuditEvent(
            event_type=event_type,
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_id=user_id,
            execution_id=execution_id,
            action=action,
            outcome=outcome,
            details=details or {},
        )
        return await self.log(event)

    async def log_security_event(
        self,
        event_type: AuditEventType,
        agent_id: str | None,
        tenant_id: str,
        resource: str,
        action: str,
        outcome: str,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Log security-related events."""
        event = AuditEvent(
            event_type=event_type,
            agent_id=agent_id,
            tenant_id=tenant_id,
            resource=resource,
            action=action,
            outcome=outcome,
            ip_address=ip_address,
            details=details or {},
        )
        return await self.log(event)

    def query(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        event_type: AuditEventType | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """
        Query audit events with filters.

        Args:
            tenant_id: Filter by tenant
            agent_id: Filter by agent
            event_type: Filter by event type
            start_time: Filter events after this time
            end_time: Filter events before this time
            user_id: Filter by user
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching audit events
        """
        results = self._events

        if tenant_id:
            results = [e for e in results if e.tenant_id == tenant_id]

        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]

        if event_type:
            results = [e for e in results if e.event_type == event_type]

        if start_time:
            results = [e for e in results if e.timestamp >= start_time]

        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        if user_id:
            results = [e for e in results if e.user_id == user_id]

        results = sorted(results, key=lambda e: e.timestamp, reverse=True)

        return results[offset : offset + limit]

    def get_agent_history(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get complete history for an agent."""
        events = self.query(agent_id=agent_id, limit=limit)
        return [e.to_dict() for e in events]

    def get_execution_trail(
        self,
        execution_id: str,
    ) -> list[dict[str, Any]]:
        """Get complete audit trail for an execution."""
        events = [e for e in self._events if e.execution_id == execution_id]
        events = sorted(events, key=lambda e: e.timestamp)
        return [e.to_dict() for e in events]

    def get_human_interactions(
        self,
        tenant_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get all human-in-the-loop interactions."""
        human_event_types = {
            AuditEventType.HUMAN_FEEDBACK_REQUESTED,
            AuditEventType.HUMAN_FEEDBACK_PROVIDED,
            AuditEventType.HUMAN_APPROVAL_GRANTED,
            AuditEventType.HUMAN_APPROVAL_DENIED,
        }

        results = [e for e in self._events if e.event_type in human_event_types]

        if tenant_id:
            results = [e for e in results if e.tenant_id == tenant_id]

        if start_time:
            results = [e for e in results if e.timestamp >= start_time]

        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        return [e.to_dict() for e in sorted(results, key=lambda e: e.timestamp, reverse=True)]

    def get_security_events(
        self,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get security-related events."""
        security_types = {
            AuditEventType.SECURITY_VIOLATION,
            AuditEventType.RATE_LIMIT_EXCEEDED,
            AuditEventType.PERMISSION_GRANTED,
            AuditEventType.PERMISSION_REVOKED,
        }

        results = [e for e in self._events if e.event_type in security_types]

        if tenant_id:
            results = [e for e in results if e.tenant_id == tenant_id]

        results = sorted(results, key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in results[:limit]]

    def get_stats(
        self,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Get audit statistics."""
        events = self._events
        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]

        event_counts: dict[str, int] = {}
        for event in events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        return {
            "total_events": len(events),
            "events_by_type": event_counts,
            "unique_agents": len(set(e.agent_id for e in events if e.agent_id)),
            "unique_users": len(set(e.user_id for e in events if e.user_id)),
        }

    def export(
        self,
        format: str = "json",
        tenant_id: str | None = None,
    ) -> Any:
        """Export audit events."""
        events = self._events
        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]

        if format == "json":
            return [e.to_dict() for e in events]
        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if events:
                writer = csv.DictWriter(output, fieldnames=events[0].to_dict().keys())
                writer.writeheader()
                for event in events:
                    writer.writerow(event.to_dict())
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def clear(self, tenant_id: str | None = None) -> int:
        """Clear audit events (for testing or retention)."""
        if tenant_id:
            original_count = len(self._events)
            self._events = [e for e in self._events if e.tenant_id != tenant_id]
            return original_count - len(self._events)
        else:
            count = len(self._events)
            self._events.clear()
            return count
