"""
Base interfaces for state persistence.

Defines abstract contracts for state storage backends.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class StateSerializer:
    """Serializes and deserializes Pydantic models for storage."""

    @staticmethod
    def serialize(obj: BaseModel) -> str:
        """Serialize a Pydantic model to JSON string."""
        return obj.model_dump_json()

    @staticmethod
    def deserialize(data: str, model_class: type[T]) -> T:
        """Deserialize JSON string to a Pydantic model."""
        return model_class.model_validate_json(data)

    @staticmethod
    def serialize_dict(obj: BaseModel) -> dict[str, Any]:
        """Serialize a Pydantic model to dict."""
        return obj.model_dump(mode="json")

    @staticmethod
    def deserialize_dict(data: dict[str, Any], model_class: type[T]) -> T:
        """Deserialize dict to a Pydantic model."""
        return model_class.model_validate(data)


class StateStore(ABC):
    """
    Abstract base class for state storage backends.

    Implementations must provide async methods for CRUD operations
    on agent state, execution history, and audit logs.
    """

    @abstractmethod
    async def save_agent_state(
        self,
        agent_id: str,
        execution_id: str,
        state: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        """
        Save agent execution state.

        Args:
            agent_id: Agent identifier
            execution_id: Execution identifier
            state: State data to persist
            ttl_seconds: Optional TTL for automatic expiration

        Returns:
            True if saved successfully
        """

    @abstractmethod
    async def get_agent_state(
        self,
        agent_id: str,
        execution_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve agent execution state.

        Args:
            agent_id: Agent identifier
            execution_id: Execution identifier

        Returns:
            State data or None if not found
        """

    @abstractmethod
    async def delete_agent_state(
        self,
        agent_id: str,
        execution_id: str,
    ) -> bool:
        """Delete agent execution state."""

    @abstractmethod
    async def list_agent_executions(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> list[str]:
        """List execution IDs for an agent."""

    @abstractmethod
    async def save_hitl_request(
        self,
        request_id: str,
        request_data: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        """Save HITL request data."""

    @abstractmethod
    async def get_hitl_request(
        self,
        request_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve HITL request data."""

    @abstractmethod
    async def update_hitl_request(
        self,
        request_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update HITL request data."""

    @abstractmethod
    async def list_hitl_requests(
        self,
        tenant_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List HITL requests with optional filters."""

    @abstractmethod
    async def save_audit_event(
        self,
        event_id: str,
        event_data: dict[str, Any],
    ) -> bool:
        """Save audit event."""

    @abstractmethod
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
        """Query audit events with filters."""

    @abstractmethod
    async def save_tenant(
        self,
        tenant_id: str,
        tenant_data: dict[str, Any],
    ) -> bool:
        """Save tenant data."""

    @abstractmethod
    async def get_tenant(
        self,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve tenant data."""

    @abstractmethod
    async def list_tenants(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List tenants with optional filters."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the storage backend is healthy."""

    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources."""
