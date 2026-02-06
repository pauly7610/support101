"""
Activity Stream backed by Redis Streams.

Provides durable, ordered event sourcing for all agent framework activity
(internal events + external webhook events). Supports consumer groups for
parallel processing and configurable retention.

Uses redis>=5.0.3 (already in requirements). Falls back to in-memory
list when Redis is unavailable.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

_REDIS_AVAILABLE = False

try:
    import redis.asyncio as aioredis

    _REDIS_AVAILABLE = True
except ImportError:
    try:
        import aioredis  # type: ignore[no-redef]

        _REDIS_AVAILABLE = True
    except ImportError:
        logger.debug("redis[async] not installed; ActivityStream will use in-memory fallback")


@dataclass
class ActivityEvent:
    """A single activity event in the stream."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    source: str = "internal"  # "internal" | "webhook" | "agent" | "system"
    agent_id: Optional[str] = None
    tenant_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_stream_entry(self) -> Dict[str, str]:
        """Serialize for Redis XADD (all values must be strings)."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "agent_id": self.agent_id or "",
            "tenant_id": self.tenant_id,
            "data": json.dumps(self.data),
            "timestamp": self.timestamp,
            "metadata": json.dumps(self.metadata),
        }

    @classmethod
    def from_stream_entry(cls, entry: Dict[bytes, bytes]) -> "ActivityEvent":
        """Deserialize from Redis XREAD result."""
        def _d(key: str) -> str:
            val = entry.get(key.encode(b"utf-8") if isinstance(key, str) else key, b"")
            return val.decode("utf-8") if isinstance(val, bytes) else str(val)

        data_str = _d("data")
        meta_str = _d("metadata")

        return cls(
            event_id=_d("event_id"),
            event_type=_d("event_type"),
            source=_d("source"),
            agent_id=_d("agent_id") or None,
            tenant_id=_d("tenant_id"),
            data=json.loads(data_str) if data_str else {},
            timestamp=_d("timestamp"),
            metadata=json.loads(meta_str) if meta_str else {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "data": self.data,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ActivityStream:
    """
    Redis Streams-backed activity stream for durable event sourcing.

    Stream key pattern: ``activity:{tenant_id}``
    Consumer group: ``agent_framework``

    Falls back to an in-memory list when Redis is unavailable.

    Usage::

        stream = ActivityStream()
        await stream.connect()
        await stream.publish(ActivityEvent(event_type="ticket.created", tenant_id="acme", ...))
        events = await stream.read("acme", count=10)
    """

    DEFAULT_GROUP = "agent_framework"
    DEFAULT_CONSUMER = "worker-1"
    DEFAULT_MAX_LEN = 100_000
    DEFAULT_RETENTION_DAYS = 30

    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_len: int = DEFAULT_MAX_LEN,
        group_name: str = DEFAULT_GROUP,
    ) -> None:
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._max_len = max_len
        self._group_name = group_name
        self._redis: Optional[Any] = None
        self._connected = False
        self._fallback: List[ActivityEvent] = []
        self._fallback_max = 5000
        self._consumers: Dict[str, List[Callable]] = {}

    @property
    def available(self) -> bool:
        return self._connected and self._redis is not None

    def _stream_key(self, tenant_id: str) -> str:
        return f"activity:{tenant_id}" if tenant_id else "activity:global"

    async def connect(self) -> bool:
        """Connect to Redis. Returns True if connected, False if falling back."""
        if not _REDIS_AVAILABLE or not self._redis_url:
            logger.info("ActivityStream: Redis not available, using in-memory fallback")
            return False

        try:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=False,
                max_connections=10,
            )
            await self._redis.ping()
            self._connected = True
            logger.info("ActivityStream: connected to Redis")
            return True
        except Exception as e:
            logger.warning("ActivityStream: Redis connection failed: %s", e)
            self._redis = None
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass
            self._redis = None
            self._connected = False

    async def publish(self, event: ActivityEvent) -> str:
        """
        Publish an event to the activity stream.

        Returns the stream entry ID (or event_id for fallback).
        """
        if not self.available:
            self._fallback.append(event)
            if len(self._fallback) > self._fallback_max:
                self._fallback = self._fallback[-self._fallback_max:]
            await self._notify_consumers(event)
            return event.event_id

        stream_key = self._stream_key(event.tenant_id)
        try:
            entry_id = await self._redis.xadd(
                stream_key,
                event.to_stream_entry(),
                maxlen=self._max_len,
                approximate=True,
            )
            await self._notify_consumers(event)
            return entry_id.decode("utf-8") if isinstance(entry_id, bytes) else str(entry_id)
        except Exception as e:
            logger.warning("ActivityStream: publish failed, using fallback: %s", e)
            self._fallback.append(event)
            return event.event_id

    async def publish_many(self, events: List[ActivityEvent]) -> int:
        """Publish multiple events. Returns count published."""
        count = 0
        for event in events:
            await self.publish(event)
            count += 1
        return count

    async def read(
        self,
        tenant_id: str,
        count: int = 100,
        start: str = "0-0",
        end: str = "+",
    ) -> List[ActivityEvent]:
        """Read events from a tenant's stream."""
        if not self.available:
            events = [e for e in self._fallback if e.tenant_id == tenant_id]
            return events[-count:]

        stream_key = self._stream_key(tenant_id)
        try:
            raw = await self._redis.xrange(stream_key, min=start, max=end, count=count)
            return [ActivityEvent.from_stream_entry(entry) for _, entry in raw]
        except Exception as e:
            logger.warning("ActivityStream: read failed: %s", e)
            return []

    async def read_latest(self, tenant_id: str, count: int = 50) -> List[ActivityEvent]:
        """Read the most recent events from a tenant's stream."""
        if not self.available:
            events = [e for e in self._fallback if e.tenant_id == tenant_id]
            return events[-count:]

        stream_key = self._stream_key(tenant_id)
        try:
            raw = await self._redis.xrevrange(stream_key, count=count)
            events = [ActivityEvent.from_stream_entry(entry) for _, entry in raw]
            events.reverse()
            return events
        except Exception as e:
            logger.warning("ActivityStream: read_latest failed: %s", e)
            return []

    async def ensure_consumer_group(self, tenant_id: str) -> bool:
        """Create consumer group for a tenant stream if it doesn't exist."""
        if not self.available:
            return False

        stream_key = self._stream_key(tenant_id)
        try:
            await self._redis.xgroup_create(
                stream_key, self._group_name, id="0", mkstream=True
            )
            return True
        except Exception:
            return True  # group already exists

    async def read_group(
        self,
        tenant_id: str,
        consumer_name: str = DEFAULT_CONSUMER,
        count: int = 10,
        block_ms: int = 0,
    ) -> List[ActivityEvent]:
        """Read events via consumer group (for parallel processing)."""
        if not self.available:
            return []

        stream_key = self._stream_key(tenant_id)
        try:
            raw = await self._redis.xreadgroup(
                self._group_name,
                consumer_name,
                {stream_key: ">"},
                count=count,
                block=block_ms if block_ms > 0 else None,
            )
            events = []
            for _, entries in raw:
                for _, entry in entries:
                    events.append(ActivityEvent.from_stream_entry(entry))
            return events
        except Exception as e:
            logger.warning("ActivityStream: read_group failed: %s", e)
            return []

    async def ack(self, tenant_id: str, *entry_ids: str) -> int:
        """Acknowledge processed events in consumer group."""
        if not self.available:
            return 0

        stream_key = self._stream_key(tenant_id)
        try:
            return await self._redis.xack(stream_key, self._group_name, *entry_ids)
        except Exception:
            return 0

    async def trim(self, tenant_id: str, max_len: Optional[int] = None) -> int:
        """Trim stream to max length."""
        if not self.available:
            return 0

        stream_key = self._stream_key(tenant_id)
        try:
            return await self._redis.xtrim(stream_key, maxlen=max_len or self._max_len)
        except Exception:
            return 0

    async def stream_length(self, tenant_id: str) -> int:
        """Get the length of a tenant's stream."""
        if not self.available:
            return len([e for e in self._fallback if e.tenant_id == tenant_id])

        stream_key = self._stream_key(tenant_id)
        try:
            return await self._redis.xlen(stream_key)
        except Exception:
            return 0

    def on_event(self, callback: Callable) -> Callable:
        """Register a callback for all published events."""
        key = "__all__"
        if key not in self._consumers:
            self._consumers[key] = []
        self._consumers[key].append(callback)
        return callback

    def on_event_type(self, event_type: str, callback: Callable) -> Callable:
        """Register a callback for a specific event type."""
        if event_type not in self._consumers:
            self._consumers[event_type] = []
        self._consumers[event_type].append(callback)
        return callback

    async def _notify_consumers(self, event: ActivityEvent) -> None:
        """Notify registered consumers of a new event."""
        callbacks = self._consumers.get("__all__", []) + self._consumers.get(
            event.event_type, []
        )
        for cb in callbacks:
            try:
                result = cb(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.debug("ActivityStream consumer error: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        """Get activity stream statistics."""
        return {
            "connected": self._connected,
            "redis_available": _REDIS_AVAILABLE,
            "fallback_events": len(self._fallback),
            "consumer_count": sum(len(v) for v in self._consumers.values()),
        }
