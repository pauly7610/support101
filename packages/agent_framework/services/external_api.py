"""
External HTTP API client for agent framework.

Provides a shared async HTTP client for calling external services
(ticketing systems, CRMs, notification services, etc.).
Users configure endpoints via environment variables.
"""

import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_HTTPX_AVAILABLE = False

try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:
    logger.debug("httpx not installed; ExternalAPIClient will use stubs")


class ExternalAPIClient:
    """
    Shared async HTTP client for external service integrations.

    Configurable env vars:
        EXTERNAL_TICKETING_URL — Ticketing system base URL (Zendesk, Jira, etc.)
        EXTERNAL_TICKETING_API_KEY — API key for ticketing system
        EXTERNAL_CRM_URL — CRM base URL (Salesforce, HubSpot, etc.)
        EXTERNAL_CRM_API_KEY — API key for CRM
        EXTERNAL_NOTIFICATION_URL — Notification service URL (Slack, PagerDuty, etc.)
        EXTERNAL_NOTIFICATION_API_KEY — API key for notifications

    Falls back to stub responses when URLs/keys are not configured.
    """

    def __init__(self) -> None:
        self._ticketing_url = os.getenv("EXTERNAL_TICKETING_URL")
        self._ticketing_key = os.getenv("EXTERNAL_TICKETING_API_KEY")
        self._crm_url = os.getenv("EXTERNAL_CRM_URL")
        self._crm_key = os.getenv("EXTERNAL_CRM_API_KEY")
        self._notification_url = os.getenv("EXTERNAL_NOTIFICATION_URL")
        self._notification_key = os.getenv("EXTERNAL_NOTIFICATION_API_KEY")
        self._client: Any | None = None

    @property
    def ticketing_available(self) -> bool:
        return bool(self._ticketing_url and self._ticketing_key and _HTTPX_AVAILABLE)

    @property
    def crm_available(self) -> bool:
        return bool(self._crm_url and self._crm_key and _HTTPX_AVAILABLE)

    @property
    def notification_available(self) -> bool:
        return bool(self._notification_url and self._notification_key and _HTTPX_AVAILABLE)

    def _ensure_client(self) -> Any | None:
        if not _HTTPX_AVAILABLE:
            return None
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # ── Ticketing System ─────────────────────────────────────────────

    async def create_external_ticket(
        self,
        subject: str,
        description: str,
        priority: str = "medium",
        customer_email: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a ticket in the external ticketing system."""
        if not self.ticketing_available:
            return {
                "ticket_created": True,
                "external_ticket_id": f"STUB-{int(datetime.utcnow().timestamp())}",
                "subject": subject,
                "priority": priority,
                "source": "stub",
                "timestamp": datetime.utcnow().isoformat(),
            }
        client = self._ensure_client()
        try:
            payload = {
                "subject": subject,
                "description": description,
                "priority": priority,
                "customer_email": customer_email,
                **(metadata or {}),
            }
            resp = await client.post(
                f"{self._ticketing_url}/tickets",
                json=payload,
                headers=self._headers(self._ticketing_key),
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "ticket_created": True,
                "external_ticket_id": data.get("id", data.get("ticket_id", "")),
                "subject": subject,
                "priority": priority,
                "source": "external",
                "response": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning("ExternalAPIClient: create_ticket failed: %s", e)
            return {
                "ticket_created": False,
                "error": str(e),
                "source": "external_error",
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def update_external_ticket(
        self, ticket_id: str, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a ticket in the external ticketing system."""
        if not self.ticketing_available:
            return {"updated": True, "ticket_id": ticket_id, "source": "stub"}
        client = self._ensure_client()
        try:
            resp = await client.patch(
                f"{self._ticketing_url}/tickets/{ticket_id}",
                json=updates,
                headers=self._headers(self._ticketing_key),
            )
            resp.raise_for_status()
            return {
                "updated": True,
                "ticket_id": ticket_id,
                "source": "external",
                "response": resp.json(),
            }
        except Exception as e:
            logger.warning("ExternalAPIClient: update_ticket failed: %s", e)
            return {"updated": False, "ticket_id": ticket_id, "error": str(e)}

    # ── CRM ──────────────────────────────────────────────────────────

    async def get_customer_profile(self, customer_id: str) -> dict[str, Any]:
        """Fetch customer profile from external CRM."""
        if not self.crm_available:
            return {
                "customer_id": customer_id,
                "name": None,
                "email": None,
                "tier": "standard",
                "lifetime_value": None,
                "source": "stub",
            }
        client = self._ensure_client()
        try:
            resp = await client.get(
                f"{self._crm_url}/customers/{customer_id}",
                headers=self._headers(self._crm_key),
            )
            resp.raise_for_status()
            data = resp.json()
            return {**data, "source": "external"}
        except Exception as e:
            logger.warning("ExternalAPIClient: get_customer_profile failed: %s", e)
            return {
                "customer_id": customer_id,
                "error": str(e),
                "source": "external_error",
            }

    # ── Notifications ────────────────────────────────────────────────

    async def send_notification(
        self,
        channel: str,
        message: str,
        urgency: str = "normal",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a notification via external service (Slack, PagerDuty, etc.)."""
        if not self.notification_available:
            return {
                "sent": True,
                "channel": channel,
                "message": message[:100],
                "source": "stub",
                "timestamp": datetime.utcnow().isoformat(),
            }
        client = self._ensure_client()
        try:
            payload = {
                "channel": channel,
                "message": message,
                "urgency": urgency,
                **(metadata or {}),
            }
            resp = await client.post(
                f"{self._notification_url}/notify",
                json=payload,
                headers=self._headers(self._notification_key),
            )
            resp.raise_for_status()
            return {
                "sent": True,
                "channel": channel,
                "source": "external",
                "response": resp.json(),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning("ExternalAPIClient: send_notification failed: %s", e)
            return {"sent": False, "error": str(e), "source": "external_error"}

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


_api_client: ExternalAPIClient | None = None


def get_external_api_client() -> ExternalAPIClient:
    global _api_client
    if _api_client is None:
        _api_client = ExternalAPIClient()
    return _api_client
