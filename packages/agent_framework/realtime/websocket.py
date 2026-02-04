"""
WebSocket support for real-time HITL updates.

Provides bidirectional communication for:
- Real-time HITL request notifications
- Agent execution status updates
- Live dashboard updates
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

try:
    from fastapi import WebSocket

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    WebSocket = Any


@dataclass
class Connection:
    """Represents a WebSocket connection."""

    connection_id: str
    websocket: Any
    tenant_id: str
    user_id: Optional[str] = None
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Features:
    - Connection lifecycle management
    - Tenant-based isolation
    - Channel subscriptions
    - Broadcast and targeted messaging
    """

    def __init__(self) -> None:
        self._connections: Dict[str, Connection] = {}
        self._tenant_connections: Dict[str, Set[str]] = {}
        self._channel_subscribers: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Connection:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            tenant_id: Tenant for isolation
            user_id: Optional user identifier
            metadata: Optional connection metadata

        Returns:
            Connection object
        """
        if FASTAPI_AVAILABLE:
            await websocket.accept()

        connection_id = str(uuid4())
        connection = Connection(
            connection_id=connection_id,
            websocket=websocket,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=metadata or {},
        )

        async with self._lock:
            self._connections[connection_id] = connection

            if tenant_id not in self._tenant_connections:
                self._tenant_connections[tenant_id] = set()
            self._tenant_connections[tenant_id].add(connection_id)

        await self._send_message(
            connection,
            {
                "type": "connected",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        return connection

    async def disconnect(self, connection_id: str) -> None:
        """Disconnect and cleanup a connection."""
        async with self._lock:
            connection = self._connections.pop(connection_id, None)
            if not connection:
                return

            tenant_conns = self._tenant_connections.get(connection.tenant_id)
            if tenant_conns:
                tenant_conns.discard(connection_id)

            for channel in connection.subscriptions:
                subs = self._channel_subscribers.get(channel)
                if subs:
                    subs.discard(connection_id)

    async def subscribe(
        self,
        connection_id: str,
        channel: str,
    ) -> bool:
        """Subscribe a connection to a channel."""
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False

            connection.subscriptions.add(channel)

            if channel not in self._channel_subscribers:
                self._channel_subscribers[channel] = set()
            self._channel_subscribers[channel].add(connection_id)

        return True

    async def unsubscribe(
        self,
        connection_id: str,
        channel: str,
    ) -> bool:
        """Unsubscribe a connection from a channel."""
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False

            connection.subscriptions.discard(channel)

            subs = self._channel_subscribers.get(channel)
            if subs:
                subs.discard(connection_id)

        return True

    async def _send_message(
        self,
        connection: Connection,
        message: Dict[str, Any],
    ) -> bool:
        """Send a message to a connection."""
        try:
            if FASTAPI_AVAILABLE:
                await connection.websocket.send_json(message)
            return True
        except Exception:
            return False

    async def send_to_connection(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """Send a message to a specific connection."""
        connection = self._connections.get(connection_id)
        if not connection:
            return False
        return await self._send_message(connection, message)

    async def send_to_user(
        self,
        tenant_id: str,
        user_id: str,
        message: Dict[str, Any],
    ) -> int:
        """Send a message to all connections for a user."""
        sent = 0
        for conn_id in list(self._tenant_connections.get(tenant_id, [])):
            connection = self._connections.get(conn_id)
            if connection and connection.user_id == user_id:
                if await self._send_message(connection, message):
                    sent += 1
        return sent

    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        message: Dict[str, Any],
    ) -> int:
        """Broadcast a message to all connections in a tenant."""
        sent = 0
        for conn_id in list(self._tenant_connections.get(tenant_id, [])):
            connection = self._connections.get(conn_id)
            if connection:
                if await self._send_message(connection, message):
                    sent += 1
        return sent

    async def broadcast_to_channel(
        self,
        channel: str,
        message: Dict[str, Any],
    ) -> int:
        """Broadcast a message to all subscribers of a channel."""
        sent = 0
        for conn_id in list(self._channel_subscribers.get(channel, [])):
            connection = self._connections.get(conn_id)
            if connection:
                if await self._send_message(connection, message):
                    sent += 1
        return sent

    async def broadcast_all(self, message: Dict[str, Any]) -> int:
        """Broadcast a message to all connections."""
        sent = 0
        for connection in list(self._connections.values()):
            if await self._send_message(connection, message):
                sent += 1
        return sent

    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Get a connection by ID."""
        return self._connections.get(connection_id)

    def get_tenant_connections(self, tenant_id: str) -> List[Connection]:
        """Get all connections for a tenant."""
        conn_ids = self._tenant_connections.get(tenant_id, set())
        return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self._connections),
            "tenants": len(self._tenant_connections),
            "channels": len(self._channel_subscribers),
            "connections_by_tenant": {
                tid: len(conns) for tid, conns in self._tenant_connections.items()
            },
        }


class WebSocketManager:
    """
    High-level WebSocket manager for agent framework.

    Provides specialized methods for HITL and agent updates.
    """

    CHANNEL_HITL = "hitl"
    CHANNEL_AGENTS = "agents"
    CHANNEL_GOVERNANCE = "governance"

    def __init__(self, connection_manager: Optional[ConnectionManager] = None) -> None:
        self.connections = connection_manager or ConnectionManager()
        self._message_handlers: Dict[str, List[Callable]] = {}

    def on_message(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a message type."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    async def handle_message(
        self,
        connection: Connection,
        message: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Handle an incoming WebSocket message."""
        msg_type = message.get("type")

        if msg_type == "subscribe":
            channel = message.get("channel")
            if channel:
                await self.connections.subscribe(connection.connection_id, channel)
                return {"type": "subscribed", "channel": channel}

        elif msg_type == "unsubscribe":
            channel = message.get("channel")
            if channel:
                await self.connections.unsubscribe(connection.connection_id, channel)
                return {"type": "unsubscribed", "channel": channel}

        elif msg_type == "ping":
            connection.last_ping = datetime.utcnow()
            return {"type": "pong", "timestamp": datetime.utcnow().isoformat()}

        handlers = self._message_handlers.get(msg_type, [])
        for handler in handlers:
            result = handler(connection, message)
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                return result

        return None

    async def notify_hitl_request(
        self,
        tenant_id: str,
        request_data: Dict[str, Any],
    ) -> int:
        """Notify about a new HITL request."""
        message = {
            "type": "hitl_request",
            "data": request_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        channel_sent = await self.connections.broadcast_to_channel(
            f"{self.CHANNEL_HITL}:{tenant_id}",
            message,
        )

        tenant_sent = await self.connections.broadcast_to_tenant(tenant_id, message)

        return max(channel_sent, tenant_sent)

    async def notify_hitl_response(
        self,
        tenant_id: str,
        request_id: str,
        response_data: Dict[str, Any],
    ) -> int:
        """Notify about a HITL response."""
        message = {
            "type": "hitl_response",
            "request_id": request_id,
            "data": response_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self.connections.broadcast_to_tenant(tenant_id, message)

    async def notify_agent_status(
        self,
        tenant_id: str,
        agent_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Notify about agent status change."""
        message = {
            "type": "agent_status",
            "agent_id": agent_id,
            "status": status,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self.connections.broadcast_to_channel(
            f"{self.CHANNEL_AGENTS}:{tenant_id}",
            message,
        )

    async def notify_execution_update(
        self,
        tenant_id: str,
        agent_id: str,
        execution_id: str,
        step: int,
        action: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Notify about execution progress."""
        message = {
            "type": "execution_update",
            "agent_id": agent_id,
            "execution_id": execution_id,
            "step": step,
            "action": action,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self.connections.broadcast_to_channel(
            f"{self.CHANNEL_AGENTS}:{tenant_id}",
            message,
        )

    async def notify_escalation(
        self,
        tenant_id: str,
        escalation_data: Dict[str, Any],
    ) -> int:
        """Notify about an escalation."""
        message = {
            "type": "escalation",
            "data": escalation_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self.connections.broadcast_to_tenant(tenant_id, message)

    async def notify_sla_breach(
        self,
        tenant_id: str,
        request_id: str,
        breach_data: Dict[str, Any],
    ) -> int:
        """Notify about SLA breach."""
        message = {
            "type": "sla_breach",
            "request_id": request_id,
            "data": breach_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self.connections.broadcast_to_tenant(tenant_id, message)
