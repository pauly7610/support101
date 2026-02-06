"""
A2A (Agent-to-Agent) Protocol core types and server.

Implements the Google A2A protocol specification for multi-vendor
agent interoperability. Each agent is described by an AgentCard
and can receive tasks via JSON-RPC 2.0.

Reference: https://google.github.io/A2A/
"""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskState(str, Enum):
    """A2A task lifecycle states."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


@dataclass
class AgentSkill:
    """Describes a capability of an A2A agent."""

    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "examples": self.examples,
        }


@dataclass
class AgentCard:
    """
    A2A Agent Card — describes an agent's identity and capabilities.

    Served at /.well-known/agent.json for discovery.
    """

    name: str
    description: str
    url: str
    version: str = "1.0.0"
    protocol_version: str = "0.2.0"
    skills: list[AgentSkill] = field(default_factory=list)
    default_input_modes: list[str] = field(default_factory=lambda: ["text/plain"])
    default_output_modes: list[str] = field(default_factory=lambda: ["text/plain"])
    capabilities: dict[str, bool] = field(
        default_factory=lambda: {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        }
    )
    authentication: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "protocolVersion": self.protocol_version,
            "skills": [s.to_dict() for s in self.skills],
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
            "capabilities": self.capabilities,
        }
        if self.authentication:
            result["authentication"] = self.authentication
        return result


@dataclass
class TextPart:
    """A text content part in an A2A message."""

    text: str
    type: str = "text"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "text": self.text}


@dataclass
class Message:
    """An A2A message containing content parts."""

    role: str  # "user" or "agent"
    parts: list[TextPart] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "parts": [p.to_dict() for p in self.parts],
        }


@dataclass
class Artifact:
    """An output artifact from task execution."""

    name: str
    parts: list[TextPart] = field(default_factory=list)
    index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "parts": [p.to_dict() for p in self.parts],
            "index": self.index,
        }


@dataclass
class TaskStatus:
    """Current status of an A2A task."""

    state: TaskState
    message: Message | None = None
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"state": self.state.value}
        if self.message:
            result["message"] = self.message.to_dict()
        if self.timestamp:
            result["timestamp"] = self.timestamp
        return result


@dataclass
class Task:
    """An A2A task representing a unit of work."""

    id: str
    status: TaskStatus
    history: list[Message] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.to_dict(),
            "history": [m.to_dict() for m in self.history],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "metadata": self.metadata,
        }


class A2AServer:
    """
    A2A Protocol server that manages tasks and dispatches to agent handlers.

    Usage:
        server = A2AServer(agent_card)
        server.register_handler("suggest_reply", handle_suggest)
        task = await server.send_task(params)
    """

    def __init__(self, agent_card: AgentCard) -> None:
        self.agent_card = agent_card
        self._tasks: dict[str, Task] = {}
        self._handlers: dict[str, Callable] = {}
        self._default_handler: Callable | None = None

    def register_handler(self, skill_id: str, handler: Callable) -> None:
        """Register a handler for a specific skill."""
        self._handlers[skill_id] = handler

    def set_default_handler(self, handler: Callable) -> None:
        """Set the default handler for unmatched tasks."""
        self._default_handler = handler

    async def handle_jsonrpc(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle a JSON-RPC 2.0 request per A2A spec."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        handlers = {
            "tasks/send": self._handle_send_task,
            "tasks/get": self._handle_get_task,
            "tasks/cancel": self._handle_cancel_task,
        }

        handler = handlers.get(method)
        if not handler:
            return self._error(req_id, -32601, f"Method not found: {method}")

        try:
            result = await handler(params)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            logger.error("A2A handler error for %s: %s", method, e)
            return self._error(req_id, -32000, str(e)[:500])

    async def _handle_send_task(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tasks/send — create and execute a task."""
        task_id = params.get("id") or str(uuid.uuid4())
        message_data = params.get("message", {})

        user_text = ""
        for part in message_data.get("parts", []):
            if part.get("type") == "text":
                user_text += part.get("text", "")

        user_message = Message(
            role="user",
            parts=[TextPart(text=user_text)],
        )

        task = Task(
            id=task_id,
            status=TaskStatus(
                state=TaskState.WORKING,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            ),
            history=[user_message],
            metadata=params.get("metadata", {}),
        )
        self._tasks[task_id] = task

        # Determine which handler to use
        skill_id = params.get("metadata", {}).get("skill_id", "")
        handler = self._handlers.get(skill_id) or self._default_handler

        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(user_text, task.metadata)
                else:
                    result = handler(user_text, task.metadata)

                response_text = result if isinstance(result, str) else str(result)

                agent_message = Message(
                    role="agent",
                    parts=[TextPart(text=response_text)],
                )

                task.history.append(agent_message)
                task.artifacts.append(
                    Artifact(
                        name="response",
                        parts=[TextPart(text=response_text)],
                    )
                )
                task.status = TaskStatus(
                    state=TaskState.COMPLETED,
                    message=agent_message,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
            except Exception as e:
                task.status = TaskStatus(
                    state=TaskState.FAILED,
                    message=Message(role="agent", parts=[TextPart(text=str(e)[:500])]),
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
        else:
            task.status = TaskStatus(
                state=TaskState.FAILED,
                message=Message(role="agent", parts=[TextPart(text="No handler registered")]),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        return task.to_dict()

    async def _handle_get_task(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tasks/get — retrieve a task by ID."""
        task_id = params.get("id", "")
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        return task.to_dict()

    async def _handle_cancel_task(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tasks/cancel — cancel a running task."""
        task_id = params.get("id", "")
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        task.status = TaskStatus(
            state=TaskState.CANCELED,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        return task.to_dict()

    def _error(self, req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }
