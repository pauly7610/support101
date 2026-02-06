"""
Redis-based state store implementation.

Provides distributed, persistent state storage with TTL support.
"""

import json
from datetime import datetime
from typing import Any

from .base import StateStore


class RedisStateStore(StateStore):
    """
    Redis implementation of StateStore.

    Supports:
    - Distributed state across multiple instances
    - TTL-based expiration
    - Pub/sub for real-time updates
    """

    KEY_PREFIX = "agent_framework"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str | None = None,
    ) -> None:
        self._redis_url = redis_url
        self._prefix = key_prefix or self.KEY_PREFIX
        self._client: Any | None = None

    async def _get_client(self) -> Any:
        """Lazy initialization of Redis client."""
        if self._client is None:
            try:
                import redis.asyncio as redis

                self._client = redis.from_url(self._redis_url, decode_responses=True)
            except ImportError:
                raise ImportError(
                    "redis package required for RedisStateStore. Install with: pip install redis"
                ) from None
        return self._client

    def _key(self, *parts: str) -> str:
        """Build a namespaced key."""
        return f"{self._prefix}:{':'.join(parts)}"

    async def save_agent_state(
        self,
        agent_id: str,
        execution_id: str,
        state: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        client = await self._get_client()
        key = self._key("state", agent_id, execution_id)
        data = json.dumps(
            {
                "agent_id": agent_id,
                "execution_id": execution_id,
                "state": state,
                "saved_at": datetime.utcnow().isoformat(),
            }
        )

        if ttl_seconds:
            await client.setex(key, ttl_seconds, data)
        else:
            await client.set(key, data)

        await client.sadd(self._key("agent_executions", agent_id), execution_id)
        return True

    async def get_agent_state(
        self,
        agent_id: str,
        execution_id: str,
    ) -> dict[str, Any] | None:
        client = await self._get_client()
        key = self._key("state", agent_id, execution_id)
        data = await client.get(key)

        if data:
            parsed = json.loads(data)
            return parsed.get("state")
        return None

    async def delete_agent_state(
        self,
        agent_id: str,
        execution_id: str,
    ) -> bool:
        client = await self._get_client()
        key = self._key("state", agent_id, execution_id)
        deleted = await client.delete(key)
        await client.srem(self._key("agent_executions", agent_id), execution_id)
        return deleted > 0

    async def list_agent_executions(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> list[str]:
        client = await self._get_client()
        key = self._key("agent_executions", agent_id)
        members = await client.smembers(key)
        return list(members)[:limit]

    async def save_hitl_request(
        self,
        request_id: str,
        request_data: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        client = await self._get_client()
        key = self._key("hitl", request_id)
        data = json.dumps(
            {
                **request_data,
                "saved_at": datetime.utcnow().isoformat(),
            }
        )

        if ttl_seconds:
            await client.setex(key, ttl_seconds, data)
        else:
            await client.set(key, data)

        tenant_id = request_data.get("tenant_id", "default")
        await client.sadd(self._key("hitl_by_tenant", tenant_id), request_id)

        status = request_data.get("status", "pending")
        await client.sadd(self._key("hitl_by_status", status), request_id)

        return True

    async def get_hitl_request(
        self,
        request_id: str,
    ) -> dict[str, Any] | None:
        client = await self._get_client()
        key = self._key("hitl", request_id)
        data = await client.get(key)
        return json.loads(data) if data else None

    async def update_hitl_request(
        self,
        request_id: str,
        updates: dict[str, Any],
    ) -> bool:
        client = await self._get_client()
        key = self._key("hitl", request_id)

        existing = await client.get(key)
        if not existing:
            return False

        data = json.loads(existing)
        old_status = data.get("status")

        data.update(updates)
        data["updated_at"] = datetime.utcnow().isoformat()

        await client.set(key, json.dumps(data))

        new_status = data.get("status")
        if old_status != new_status:
            if old_status:
                await client.srem(self._key("hitl_by_status", old_status), request_id)
            if new_status:
                await client.sadd(self._key("hitl_by_status", new_status), request_id)

        return True

    async def list_hitl_requests(
        self,
        tenant_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        client = await self._get_client()

        if tenant_id and status:
            tenant_key = self._key("hitl_by_tenant", tenant_id)
            status_key = self._key("hitl_by_status", status)
            request_ids = await client.sinter(tenant_key, status_key)
        elif tenant_id:
            request_ids = await client.smembers(self._key("hitl_by_tenant", tenant_id))
        elif status:
            request_ids = await client.smembers(self._key("hitl_by_status", status))
        else:
            pattern = self._key("hitl", "*")
            keys = []
            async for key in client.scan_iter(match=pattern, count=limit):
                keys.append(key)
                if len(keys) >= limit:
                    break
            request_ids = [k.split(":")[-1] for k in keys]

        results = []
        for rid in list(request_ids)[:limit]:
            data = await self.get_hitl_request(rid)
            if data:
                results.append(data)

        return results

    async def save_audit_event(
        self,
        event_id: str,
        event_data: dict[str, Any],
    ) -> bool:
        client = await self._get_client()
        key = self._key("audit", event_id)
        await client.set(key, json.dumps(event_data))

        timestamp = event_data.get("timestamp", datetime.utcnow().isoformat())
        await client.zadd(
            self._key("audit_timeline"),
            {event_id: datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()},
        )

        tenant_id = event_data.get("tenant_id")
        if tenant_id:
            await client.zadd(
                self._key("audit_by_tenant", tenant_id),
                {event_id: datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()},
            )

        return True

    async def query_audit_events(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        client = await self._get_client()

        if tenant_id:
            timeline_key = self._key("audit_by_tenant", tenant_id)
        else:
            timeline_key = self._key("audit_timeline")

        min_score = start_time.timestamp() if start_time else "-inf"
        max_score = end_time.timestamp() if end_time else "+inf"

        event_ids = await client.zrevrangebyscore(
            timeline_key,
            max_score,
            min_score,
            start=offset,
            num=limit * 2,
        )

        results = []
        for eid in event_ids:
            data = await client.get(self._key("audit", eid))
            if data:
                event = json.loads(data)
                if agent_id and event.get("agent_id") != agent_id:
                    continue
                if event_type and event.get("event_type") != event_type:
                    continue
                results.append(event)
                if len(results) >= limit:
                    break

        return results

    async def save_tenant(
        self,
        tenant_id: str,
        tenant_data: dict[str, Any],
    ) -> bool:
        client = await self._get_client()
        key = self._key("tenant", tenant_id)
        await client.set(key, json.dumps(tenant_data))

        status = tenant_data.get("status", "pending")
        await client.sadd(self._key("tenants_by_status", status), tenant_id)
        await client.sadd(self._key("all_tenants"), tenant_id)

        return True

    async def get_tenant(
        self,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        client = await self._get_client()
        key = self._key("tenant", tenant_id)
        data = await client.get(key)
        return json.loads(data) if data else None

    async def list_tenants(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        client = await self._get_client()

        if status:
            tenant_ids = await client.smembers(self._key("tenants_by_status", status))
        else:
            tenant_ids = await client.smembers(self._key("all_tenants"))

        results = []
        for tid in list(tenant_ids)[:limit]:
            data = await self.get_tenant(tid)
            if data:
                results.append(data)

        return results

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def publish(self, channel: str, message: dict[str, Any]) -> int:
        """Publish a message to a Redis channel (for real-time updates)."""
        client = await self._get_client()
        return await client.publish(
            self._key("channel", channel),
            json.dumps(message),
        )

    async def subscribe(self, channel: str) -> Any:
        """Subscribe to a Redis channel."""
        client = await self._get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(self._key("channel", channel))
        return pubsub
