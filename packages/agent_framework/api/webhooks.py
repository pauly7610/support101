"""
Inbound Webhook API Endpoints.

Receives events from external systems (Zendesk, Slack, Jira, etc.)
and publishes them to the ActivityStream for processing by the
learning system and activity graph.

Supports HMAC signature verification per provider.
"""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

_activity_stream = None
_feedback_collector = None
_webhook_secrets: dict[str, str] = {}


def configure_webhooks(
    activity_stream: Any = None,
    feedback_collector: Any = None,
    secrets: dict[str, str] | None = None,
) -> None:
    """Configure webhook dependencies. Called from SDK initialization."""
    global _activity_stream, _feedback_collector, _webhook_secrets
    _activity_stream = activity_stream
    _feedback_collector = feedback_collector
    _webhook_secrets = secrets or {}


def get_activity_stream():
    return _activity_stream


def get_feedback_collector():
    return _feedback_collector


# ── Request Models ────────────────────────────────────────────


class WebhookPayload(BaseModel):
    """Generic webhook payload."""

    event_type: str = Field(..., description="Event type (e.g. ticket.updated)")
    external_id: str = Field(default="", description="ID in the source system")
    tenant_id: str = Field(default="", description="Tenant ID for isolation")
    data: dict[str, Any] = Field(default_factory=dict, description="Provider-specific payload")
    timestamp: str | None = Field(default=None, description="ISO timestamp")


class ZendeskWebhookPayload(BaseModel):
    """Zendesk webhook payload."""

    ticket_id: str = ""
    event_type: str = ""  # ticket.created, ticket.updated, ticket.solved, comment.added
    status: str = ""
    priority: str = ""
    subject: str = ""
    description: str = ""
    assignee_id: str = ""
    requester_id: str = ""
    satisfaction_rating: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class SlackWebhookPayload(BaseModel):
    """Slack webhook payload."""

    event_type: str = ""  # message.posted, reaction.added, thread.reply
    channel: str = ""
    user_id: str = ""
    text: str = ""
    thread_ts: str = ""
    reaction: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class JiraWebhookPayload(BaseModel):
    """Jira webhook payload."""

    issue_key: str = ""
    event_type: str = ""  # issue.created, issue.updated, issue.transitioned, comment.added
    status: str = ""
    priority: str = ""
    summary: str = ""
    assignee: str = ""
    reporter: str = ""
    comment: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)


# ── Signature Verification ────────────────────────────────────


def _verify_signature(
    provider: str,
    body: bytes,
    signature: str | None,
) -> bool:
    """Verify HMAC signature for a webhook provider."""
    secret = _webhook_secrets.get(provider)
    if not secret:
        return True  # no secret configured = skip verification

    if not signature:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Support "sha256=<hex>" format (GitHub/Zendesk style)
    sig_value = signature.split("=", 1)[-1] if "=" in signature else signature

    return hmac.compare_digest(expected, sig_value)


# ── Endpoints ─────────────────────────────────────────────────


@router.post("/generic", status_code=status.HTTP_202_ACCEPTED)
async def receive_generic_webhook(
    payload: WebhookPayload,
    request: Request,
    x_webhook_signature: str | None = Header(None),
) -> dict[str, Any]:
    """Receive a generic webhook event."""
    body = await request.body()
    if not _verify_signature("generic", body, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    stream = get_activity_stream()
    if stream is None:
        return {"status": "accepted", "warning": "activity stream not configured"}

    from ..learning.activity_stream import ActivityEvent

    event = ActivityEvent(
        event_type=payload.event_type,
        source="webhook",
        tenant_id=payload.tenant_id,
        data=payload.data,
        timestamp=payload.timestamp or datetime.utcnow().isoformat(),
        metadata={"external_id": payload.external_id, "provider": "generic"},
    )
    entry_id = await stream.publish(event)
    return {"status": "accepted", "entry_id": entry_id}


@router.post("/zendesk", status_code=status.HTTP_202_ACCEPTED)
async def receive_zendesk_webhook(
    payload: ZendeskWebhookPayload,
    request: Request,
    x_zendesk_webhook_signature: str | None = Header(None),
    x_tenant_id: str = Header(default=""),
) -> dict[str, Any]:
    """Receive a Zendesk webhook event."""
    body = await request.body()
    if not _verify_signature("zendesk", body, x_zendesk_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid Zendesk signature")

    stream = get_activity_stream()
    if stream is None:
        return {"status": "accepted", "warning": "activity stream not configured"}

    from ..learning.activity_stream import ActivityEvent

    event = ActivityEvent(
        event_type=(f"zendesk.{payload.event_type}" if payload.event_type else "zendesk.unknown"),
        source="webhook",
        tenant_id=x_tenant_id,
        data={
            "ticket_id": payload.ticket_id,
            "status": payload.status,
            "priority": payload.priority,
            "subject": payload.subject,
            "description": payload.description[:2000] if payload.description else "",
            "assignee_id": payload.assignee_id,
            "requester_id": payload.requester_id,
            "tags": payload.tags,
            "custom_fields": payload.custom_fields,
        },
        metadata={"provider": "zendesk", "external_id": payload.ticket_id},
    )
    entry_id = await stream.publish(event)

    # Handle CSAT signals
    collector = get_feedback_collector()
    if collector and payload.satisfaction_rating:
        score = payload.satisfaction_rating.get("score", 0)
        if isinstance(score, str):
            score = {"good": 5.0, "bad": 1.0, "offered": 3.0}.get(score, 3.0)
        try:
            await collector.record_csat(
                ticket_id=payload.ticket_id,
                score=float(score),
                trace={
                    "input_query": payload.subject,
                    "category": "zendesk",
                    "agent_blueprint": "",
                    "steps": [],
                    "output": {"response": payload.description[:500]},
                },
                tenant_id=x_tenant_id,
            )
        except Exception as e:
            logger.debug("Zendesk CSAT recording failed: %s", e)

    return {"status": "accepted", "entry_id": entry_id}


@router.post("/slack", status_code=status.HTTP_202_ACCEPTED)
async def receive_slack_webhook(
    payload: SlackWebhookPayload,
    request: Request,
    x_slack_signature: str | None = Header(None),
    x_tenant_id: str = Header(default=""),
) -> dict[str, Any]:
    """Receive a Slack webhook event."""
    body = await request.body()
    if not _verify_signature("slack", body, x_slack_signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    stream = get_activity_stream()
    if stream is None:
        return {"status": "accepted", "warning": "activity stream not configured"}

    from ..learning.activity_stream import ActivityEvent

    event = ActivityEvent(
        event_type=(f"slack.{payload.event_type}" if payload.event_type else "slack.unknown"),
        source="webhook",
        tenant_id=x_tenant_id,
        data={
            "channel": payload.channel,
            "user_id": payload.user_id,
            "text": payload.text[:2000] if payload.text else "",
            "thread_ts": payload.thread_ts,
            "reaction": payload.reaction,
        },
        metadata={"provider": "slack", **payload.metadata},
    )
    entry_id = await stream.publish(event)
    return {"status": "accepted", "entry_id": entry_id}


@router.post("/jira", status_code=status.HTTP_202_ACCEPTED)
async def receive_jira_webhook(
    payload: JiraWebhookPayload,
    request: Request,
    x_hub_signature: str | None = Header(None),
    x_tenant_id: str = Header(default=""),
) -> dict[str, Any]:
    """Receive a Jira webhook event."""
    body = await request.body()
    if not _verify_signature("jira", body, x_hub_signature):
        raise HTTPException(status_code=401, detail="Invalid Jira signature")

    stream = get_activity_stream()
    if stream is None:
        return {"status": "accepted", "warning": "activity stream not configured"}

    from ..learning.activity_stream import ActivityEvent

    event = ActivityEvent(
        event_type=(f"jira.{payload.event_type}" if payload.event_type else "jira.unknown"),
        source="webhook",
        tenant_id=x_tenant_id,
        data={
            "issue_key": payload.issue_key,
            "status": payload.status,
            "priority": payload.priority,
            "summary": payload.summary,
            "assignee": payload.assignee,
            "reporter": payload.reporter,
            "comment": payload.comment[:2000] if payload.comment else "",
            "fields": payload.fields,
        },
        metadata={"provider": "jira", "external_id": payload.issue_key},
    )
    entry_id = await stream.publish(event)
    return {"status": "accepted", "entry_id": entry_id}


@router.get("/stats")
async def get_webhook_stats() -> dict[str, Any]:
    """Get webhook and activity stream statistics."""
    stream = get_activity_stream()
    return {
        "activity_stream": stream.get_stats() if stream else {"connected": False},
        "configured_providers": (list(_webhook_secrets.keys()) if _webhook_secrets else []),
    }
