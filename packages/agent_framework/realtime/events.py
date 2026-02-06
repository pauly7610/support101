"""
Event bus for internal agent framework events.

Provides pub/sub pattern for decoupled communication.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class EventType(StrEnum):
    """Types of framework events."""

    AGENT_CREATED = "agent.created"
    AGENT_DELETED = "agent.deleted"
    AGENT_UPDATED = "agent.updated"

    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    EXECUTION_STEP = "execution.step"

    HITL_REQUEST_CREATED = "hitl.request.created"
    HITL_REQUEST_ASSIGNED = "hitl.request.assigned"
    HITL_REQUEST_RESPONDED = "hitl.request.responded"
    HITL_REQUEST_EXPIRED = "hitl.request.expired"
    HITL_SLA_BREACH = "hitl.sla.breach"

    ESCALATION_TRIGGERED = "escalation.triggered"
    ESCALATION_RESOLVED = "escalation.resolved"

    TENANT_CREATED = "tenant.created"
    TENANT_ACTIVATED = "tenant.activated"
    TENANT_SUSPENDED = "tenant.suspended"
    TENANT_LIMIT_REACHED = "tenant.limit.reached"

    CIRCUIT_BREAKER_OPENED = "circuit.opened"
    CIRCUIT_BREAKER_CLOSED = "circuit.closed"


@dataclass
class Event:
    """An event in the event bus."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: EventType = EventType.AGENT_CREATED
    tenant_id: str | None = None
    agent_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class EventBus:
    """
    Async event bus for framework-wide events.

    Features:
    - Async event publishing
    - Multiple subscribers per event type
    - Wildcard subscriptions
    - Event filtering by tenant
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = {}
        self._wildcard_subscribers: list[Callable] = []
        self._event_history: list[Event] = []
        self._max_history: int = 1000
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Any],
    ) -> Callable[[], None]:
        """
        Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to
            handler: Async or sync callback function

        Returns:
            Unsubscribe function
        """
        key = event_type.value
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(handler)

        def unsubscribe():
            if key in self._subscribers:
                self._subscribers[key].remove(handler)

        return unsubscribe

    def subscribe_all(self, handler: Callable[[Event], Any]) -> Callable[[], None]:
        """Subscribe to all events."""
        self._wildcard_subscribers.append(handler)

        def unsubscribe():
            self._wildcard_subscribers.remove(handler)

        return unsubscribe

    async def publish(self, event: Event) -> int:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish

        Returns:
            Number of handlers notified
        """
        async with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history :]

        handlers_called = 0

        key = event.event_type.value
        handlers = self._subscribers.get(key, []) + self._wildcard_subscribers

        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
                handlers_called += 1
            except Exception as e:
                print(f"Event handler error for {key}: {e}")

        return handlers_called

    async def publish_many(self, events: list[Event]) -> int:
        """Publish multiple events."""
        total = 0
        for event in events:
            total += await self.publish(event)
        return total

    def emit(
        self,
        event_type: EventType,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> asyncio.Task:
        """
        Convenience method to create and publish an event.

        Returns an asyncio Task for the publish operation.
        """
        event = Event(
            event_type=event_type,
            tenant_id=tenant_id,
            agent_id=agent_id,
            data=data or {},
            metadata=kwargs,
        )
        return asyncio.create_task(self.publish(event))

    def get_history(
        self,
        event_type: EventType | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get event history with optional filters."""
        events = self._event_history.copy()

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]

        return events[-limit:]

    def clear_history(self) -> int:
        """Clear event history."""
        count = len(self._event_history)
        self._event_history.clear()
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics."""
        event_counts: dict[str, int] = {}
        for event in self._event_history:
            key = event.event_type.value
            event_counts[key] = event_counts.get(key, 0) + 1

        return {
            "total_events": len(self._event_history),
            "subscriber_count": sum(len(h) for h in self._subscribers.values()),
            "wildcard_subscribers": len(self._wildcard_subscribers),
            "events_by_type": event_counts,
        }

    def bridge_to_activity_stream(self, activity_stream: Any) -> None:
        """Bridge all EventBus events to an ActivityStream for durable persistence."""
        from ..learning.activity_stream import ActivityEvent

        async def _forward(event: Event) -> None:
            try:
                ae = ActivityEvent(
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    source="internal",
                    agent_id=event.agent_id,
                    tenant_id=event.tenant_id or "",
                    data=event.data,
                    timestamp=event.timestamp.isoformat(),
                    metadata=event.metadata,
                )
                await activity_stream.publish(ae)
            except Exception as e:
                print(f"EventBus→ActivityStream bridge error: {e}")

        self.subscribe_all(_forward)


_default_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the default event bus."""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus
