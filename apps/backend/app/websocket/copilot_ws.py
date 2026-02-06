"""
WebSocket endpoint for real-time Agent Copilot suggestions.

Provides bidirectional communication between the Chrome extension sidebar
and the backend RAG/agent framework. Supports:
- Ticket context streaming from the extension
- Real-time suggested replies
- Connection health via ping/pong
- JWT authentication on connect
"""

import asyncio
import json
import os
import time
from typing import Any

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

router = APIRouter(tags=["WebSocket"])

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret")
JWT_ALGORITHM = "HS256"

# Active connections registry
_connections: set[WebSocket] = set()


def _verify_token(token: str) -> dict[str, Any] | None:
    """Verify JWT token and return payload, or None if invalid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def _generate_suggestion(ticket_context: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a suggested reply for the given ticket context.
    Uses RAG chain if available, falls back to echo response.
    """
    try:
        from packages.llm_engine.chains.rag_chain import RAGChain

        chain = RAGChain()
        question = ticket_context.get("content") or ticket_context.get("user_query", "")
        if not question:
            return {
                "type": "suggestion",
                "reply_text": None,
                "sources": [],
                "error": "No content provided in ticket context",
            }
        result = await asyncio.wait_for(chain.generate(question), timeout=30)
        if "error_type" in result:
            return {"type": "error", **result}
        return {
            "type": "suggestion",
            "reply_text": result.get("reply"),
            "sources": result.get("sources", []),
            "generated_at": time.time(),
        }
    except ImportError:
        return {
            "type": "suggestion",
            "reply_text": f"[Mock] Suggested reply for: {ticket_context.get('content', '')[:100]}",
            "sources": [],
            "generated_at": time.time(),
            "mock": True,
        }
    except TimeoutError:
        return {
            "type": "error",
            "error_type": "llm_timeout",
            "message": "LLM response exceeded 30s threshold",
            "retryable": True,
            "documentation": "https://api.support101/errors#E429",
        }
    except Exception as e:
        return {
            "type": "error",
            "error_type": "suggestion_error",
            "message": str(e)[:200],
            "retryable": True,
            "documentation": "https://api.support101/errors#E500",
        }


@router.websocket("/ws/copilot")
async def copilot_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for the Agent Copilot Chrome extension.

    Protocol:
    1. Client connects with ?token=<JWT> query param
    2. Server validates token, accepts or rejects
    3. Client sends JSON messages:
       - {"type": "ticket_context", "data": {...}}  → triggers suggestion
       - {"type": "ping"}                           → server replies pong
    4. Server sends JSON messages:
       - {"type": "suggestion", "reply_text": ..., "sources": [...]}
       - {"type": "error", "error_type": ..., "message": ...}
       - {"type": "pong", "timestamp": ...}
       - {"type": "connected", "message": ...}
    """
    token = websocket.query_params.get("token")

    if token:
        payload = _verify_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    else:
        # Allow unauthenticated connections in dev mode
        if os.getenv("ENVIRONMENT", "development") == "production":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket.accept()
    _connections.add(websocket)

    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Copilot WebSocket connected",
            "timestamp": time.time(),
        })

        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error_type": "invalid_json",
                    "message": "Invalid JSON payload",
                    "retryable": False,
                    "documentation": "https://api.support101/errors#E400",
                })
                continue

            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": time.time(),
                })

            elif msg_type == "ticket_context":
                ticket_data = message.get("data", {})
                await websocket.send_json({
                    "type": "processing",
                    "message": "Generating suggestion...",
                })
                suggestion = await _generate_suggestion(ticket_data)
                await websocket.send_json(suggestion)

            else:
                await websocket.send_json({
                    "type": "error",
                    "error_type": "unknown_message_type",
                    "message": f"Unknown message type: {msg_type}",
                    "retryable": False,
                    "documentation": "https://api.support101/errors#E400",
                })

    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)


async def broadcast(message: dict[str, Any]) -> None:
    """Broadcast a message to all connected copilot clients."""
    dead: set[WebSocket] = set()
    for ws in _connections:  # noqa: F823
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    _connections -= dead


def get_connection_count() -> int:
    """Return the number of active WebSocket connections."""
    return len(_connections)
