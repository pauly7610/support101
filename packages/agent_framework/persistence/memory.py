"""
In-memory state store implementation.

Useful for development, testing, and single-instance deployments.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import StateStore


class InMemoryStateStore(StateStore):
    """
    In-memory implementation of StateStore.

    Data is lost on restart. Use for development/testing only.
    """

    def __init__(self) -> None:
        self._agent_states: Dict[str, Dict[str, Any]] = {}
        self._hitl_requests: Dict[str, Dict[str, Any]] = {}
        self._audit_events: List[Dict[str, Any]] = []
        self._tenants: Dict[str, Dict[str, Any]] = {}

    def _state_key(self, agent_id: str, execution_id: str) -> str:
        return f"{agent_id}:{execution_id}"

    async def save_agent_state(
        self,
        agent_id: str,
        execution_id: str,
        state: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        key = self._state_key(agent_id, execution_id)
        self._agent_states[key] = {
            "agent_id": agent_id,
            "execution_id": execution_id,
            "state": state,
            "saved_at": datetime.utcnow().isoformat(),
        }
        return True

    async def get_agent_state(
        self,
        agent_id: str,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        key = self._state_key(agent_id, execution_id)
        data = self._agent_states.get(key)
        return data.get("state") if data else None

    async def delete_agent_state(
        self,
        agent_id: str,
        execution_id: str,
    ) -> bool:
        key = self._state_key(agent_id, execution_id)
        if key in self._agent_states:
            del self._agent_states[key]
            return True
        return False

    async def list_agent_executions(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> List[str]:
        executions = [
            data["execution_id"]
            for key, data in self._agent_states.items()
            if data.get("agent_id") == agent_id
        ]
        return executions[:limit]

    async def save_hitl_request(
        self,
        request_id: str,
        request_data: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        self._hitl_requests[request_id] = {
            **request_data,
            "saved_at": datetime.utcnow().isoformat(),
        }
        return True

    async def get_hitl_request(
        self,
        request_id: str,
    ) -> Optional[Dict[str, Any]]:
        return self._hitl_requests.get(request_id)

    async def update_hitl_request(
        self,
        request_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        if request_id not in self._hitl_requests:
            return False
        self._hitl_requests[request_id].update(updates)
        self._hitl_requests[request_id]["updated_at"] = datetime.utcnow().isoformat()
        return True

    async def list_hitl_requests(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        results = list(self._hitl_requests.values())

        if tenant_id:
            results = [r for r in results if r.get("tenant_id") == tenant_id]
        if status:
            results = [r for r in results if r.get("status") == status]

        return results[:limit]

    async def save_audit_event(
        self,
        event_id: str,
        event_data: Dict[str, Any],
    ) -> bool:
        self._audit_events.append(
            {
                "event_id": event_id,
                **event_data,
            }
        )
        return True

    async def query_audit_events(
        self,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        results = self._audit_events.copy()

        if tenant_id:
            results = [e for e in results if e.get("tenant_id") == tenant_id]
        if agent_id:
            results = [e for e in results if e.get("agent_id") == agent_id]
        if event_type:
            results = [e for e in results if e.get("event_type") == event_type]

        results = sorted(results, key=lambda e: e.get("timestamp", ""), reverse=True)
        return results[offset : offset + limit]

    async def save_tenant(
        self,
        tenant_id: str,
        tenant_data: Dict[str, Any],
    ) -> bool:
        self._tenants[tenant_id] = tenant_data
        return True

    async def get_tenant(
        self,
        tenant_id: str,
    ) -> Optional[Dict[str, Any]]:
        return self._tenants.get(tenant_id)

    async def list_tenants(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        results = list(self._tenants.values())
        if status:
            results = [t for t in results if t.get("status") == status]
        return results[:limit]

    async def health_check(self) -> bool:
        return True

    async def close(self) -> None:
        pass

    def clear(self) -> None:
        """Clear all stored data (for testing)."""
        self._agent_states.clear()
        self._hitl_requests.clear()
        self._audit_events.clear()
        self._tenants.clear()
