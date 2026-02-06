"""
LLM Cost Tracking — per-request token counting, budget alerts, and cost dashboard.

Tracks token usage and estimated costs across all LLM providers.
Persists records to PostgreSQL for durability with an in-memory write-through cache.

Environment variables:
    LLM_BUDGET_MONTHLY_USD: Monthly budget in USD (default: 100.0)
    LLM_BUDGET_ALERT_THRESHOLD: Alert at this % of budget (default: 0.8)
    LLM_COST_TRACKING_ENABLED: Enable/disable tracking (default: true)
"""

import asyncio
import logging
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── Pricing per 1M tokens (as of Feb 2026) ──────────────────────

MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    # Google
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    # Local (free)
    "llama3.2": {"input": 0.0, "output": 0.0},
    "mistral": {"input": 0.0, "output": 0.0},
}

DEFAULT_PRICING: dict[str, float] = {"input": 2.50, "output": 10.00}

MONTHLY_BUDGET_USD = float(os.getenv("LLM_BUDGET_MONTHLY_USD", "100.0"))
ALERT_THRESHOLD = float(os.getenv("LLM_BUDGET_ALERT_THRESHOLD", "0.8"))
TRACKING_ENABLED = os.getenv("LLM_COST_TRACKING_ENABLED", "true").lower() == "true"


@dataclass
class UsageRecord:
    """A single LLM usage record."""

    timestamp: float
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    request_type: str = "chat"
    tenant_id: str = ""
    agent_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetAlert:
    """A budget alert event."""

    timestamp: float
    message: str
    current_spend_usd: float
    budget_usd: float
    percentage: float


class CostTracker:
    """
    Tracks LLM token usage and costs across all providers.

    Thread-safe. Persists records to PostgreSQL via SQLAlchemy async engine.
    Maintains an in-memory cache for fast dashboard reads.
    Falls back to in-memory-only when the database is unavailable.
    """

    def __init__(
        self,
        monthly_budget_usd: float = MONTHLY_BUDGET_USD,
        alert_threshold: float = ALERT_THRESHOLD,
    ) -> None:
        self._records: list[UsageRecord] = []
        self._alerts: list[BudgetAlert] = []
        self._lock = threading.Lock()
        self.monthly_budget_usd = monthly_budget_usd
        self.alert_threshold = alert_threshold
        self._alert_sent_this_period = False
        self._db_available = False
        self._hydrated = False

    async def _get_session(self):
        """Get an async DB session. Returns None if DB is unavailable."""
        try:
            from apps.backend.app.core.db import SessionLocal

            return SessionLocal()
        except Exception:
            return None

    async def _persist_record(self, record: UsageRecord) -> None:
        """Persist a usage record to the database."""
        session = await self._get_session()
        if session is None:
            return
        try:
            from apps.backend.app.analytics.models import LLMUsageRecord

            db_record = LLMUsageRecord(
                timestamp=record.timestamp,
                model=record.model,
                provider=record.provider,
                prompt_tokens=record.prompt_tokens,
                completion_tokens=record.completion_tokens,
                total_tokens=record.total_tokens,
                estimated_cost_usd=record.estimated_cost_usd,
                request_type=record.request_type,
                tenant_id=record.tenant_id,
                agent_id=record.agent_id,
                metadata_=record.metadata,
            )
            session.add(db_record)
            await session.commit()
            self._db_available = True
        except Exception as e:
            logger.debug("Cost tracker DB persist failed (falling back to memory): %s", e)
            await session.rollback()
        finally:
            await session.close()

    async def _persist_alert(self, alert: BudgetAlert) -> None:
        """Persist a budget alert to the database."""
        session = await self._get_session()
        if session is None:
            return
        try:
            from apps.backend.app.analytics.models import LLMBudgetAlert

            db_alert = LLMBudgetAlert(
                timestamp=alert.timestamp,
                message=alert.message,
                current_spend_usd=alert.current_spend_usd,
                budget_usd=alert.budget_usd,
                percentage=alert.percentage,
            )
            session.add(db_alert)
            await session.commit()
        except Exception as e:
            logger.debug("Cost tracker DB alert persist failed: %s", e)
            await session.rollback()
        finally:
            await session.close()

    async def hydrate_from_db(self) -> None:
        """Load existing records from DB into in-memory cache on startup."""
        if self._hydrated:
            return
        session = await self._get_session()
        if session is None:
            self._hydrated = True
            return
        try:
            from sqlalchemy import select

            from apps.backend.app.analytics.models import LLMBudgetAlert, LLMUsageRecord

            now = datetime.utcnow()
            thirty_days_ago = (now - timedelta(days=30)).timestamp()

            result = await session.execute(
                select(LLMUsageRecord).where(LLMUsageRecord.timestamp >= thirty_days_ago)
            )
            rows = result.scalars().all()

            with self._lock:
                for row in rows:
                    self._records.append(
                        UsageRecord(
                            timestamp=row.timestamp,
                            model=row.model,
                            provider=row.provider,
                            prompt_tokens=row.prompt_tokens,
                            completion_tokens=row.completion_tokens,
                            total_tokens=row.total_tokens,
                            estimated_cost_usd=row.estimated_cost_usd,
                            request_type=row.request_type or "chat",
                            tenant_id=row.tenant_id or "",
                            agent_id=row.agent_id or "",
                            metadata=row.metadata_ or {},
                        )
                    )

            alert_result = await session.execute(
                select(LLMBudgetAlert).where(LLMBudgetAlert.timestamp >= thirty_days_ago)
            )
            alert_rows = alert_result.scalars().all()
            with self._lock:
                for row in alert_rows:
                    self._alerts.append(
                        BudgetAlert(
                            timestamp=row.timestamp,
                            message=row.message,
                            current_spend_usd=row.current_spend_usd,
                            budget_usd=row.budget_usd,
                            percentage=row.percentage,
                        )
                    )

            self._db_available = True
            logger.info(
                "Cost tracker hydrated %d records and %d alerts from DB",
                len(rows),
                len(alert_rows),
            )
        except Exception as e:
            logger.debug("Cost tracker DB hydration failed (using empty cache): %s", e)
        finally:
            self._hydrated = True
            await session.close()

    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        provider: str = "openai",
        request_type: str = "chat",
        tenant_id: str = "",
        agent_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> UsageRecord:
        """
        Record a single LLM API call's token usage.

        Returns the UsageRecord with estimated cost.
        Persists to DB asynchronously (fire-and-forget).
        """
        if not TRACKING_ENABLED:
            return UsageRecord(
                timestamp=time.time(),
                model=model,
                provider=provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=0.0,
            )

        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        record = UsageRecord(
            timestamp=time.time(),
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=total_cost,
            request_type=request_type,
            tenant_id=tenant_id,
            agent_id=agent_id,
            metadata=metadata or {},
        )

        with self._lock:
            self._records.append(record)
            self._check_budget()

        # Fire-and-forget DB persistence
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._persist_record(record))
        except RuntimeError:
            pass  # No event loop — skip DB persistence (e.g. in sync tests)

        return record

    def _check_budget(self) -> None:
        """Check if spending has exceeded the alert threshold."""
        current_spend = self._get_current_month_spend()
        percentage = current_spend / self.monthly_budget_usd if self.monthly_budget_usd > 0 else 0

        if percentage >= self.alert_threshold and not self._alert_sent_this_period:
            alert = BudgetAlert(
                timestamp=time.time(),
                message=f"LLM spending at {percentage:.0%} of monthly budget (${current_spend:.2f} / ${self.monthly_budget_usd:.2f})",
                current_spend_usd=current_spend,
                budget_usd=self.monthly_budget_usd,
                percentage=percentage,
            )
            self._alerts.append(alert)
            self._alert_sent_this_period = True
            logger.warning("BUDGET ALERT: %s", alert.message)

            # Fire-and-forget alert persistence
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._persist_alert(alert))
            except RuntimeError:
                pass

        if percentage >= 1.0:
            logger.error(
                "BUDGET EXCEEDED: $%.2f / $%.2f (%.0f%%)",
                current_spend,
                self.monthly_budget_usd,
                percentage * 100,
            )

    def _get_current_month_spend(self) -> float:
        """Get total spend for the current calendar month."""
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1).timestamp()
        return sum(r.estimated_cost_usd for r in self._records if r.timestamp >= month_start)

    def get_dashboard(self) -> dict[str, Any]:
        """
        Get a cost dashboard summary.

        Returns:
            Dict with current month spend, budget status, per-model breakdown,
            per-tenant breakdown, recent alerts, and daily trend.
        """
        with self._lock:
            now = datetime.utcnow()
            month_start = datetime(now.year, now.month, 1).timestamp()
            month_records = [r for r in self._records if r.timestamp >= month_start]

            # Per-model breakdown
            by_model: dict[str, dict[str, Any]] = defaultdict(
                lambda: {"requests": 0, "tokens": 0, "cost_usd": 0.0}
            )
            for r in month_records:
                by_model[r.model]["requests"] += 1
                by_model[r.model]["tokens"] += r.total_tokens
                by_model[r.model]["cost_usd"] += r.estimated_cost_usd

            # Per-tenant breakdown
            by_tenant: dict[str, dict[str, Any]] = defaultdict(
                lambda: {"requests": 0, "tokens": 0, "cost_usd": 0.0}
            )
            for r in month_records:
                tid = r.tenant_id or "default"
                by_tenant[tid]["requests"] += 1
                by_tenant[tid]["tokens"] += r.total_tokens
                by_tenant[tid]["cost_usd"] += r.estimated_cost_usd

            # Daily trend (last 30 days)
            daily: dict[str, dict[str, Any]] = defaultdict(
                lambda: {"requests": 0, "tokens": 0, "cost_usd": 0.0}
            )
            thirty_days_ago = (now - timedelta(days=30)).timestamp()
            for r in self._records:
                if r.timestamp >= thirty_days_ago:
                    day = datetime.utcfromtimestamp(r.timestamp).strftime("%Y-%m-%d")
                    daily[day]["requests"] += 1
                    daily[day]["tokens"] += r.total_tokens
                    daily[day]["cost_usd"] += r.estimated_cost_usd

            current_spend = sum(r.estimated_cost_usd for r in month_records)
            total_tokens = sum(r.total_tokens for r in month_records)
            total_requests = len(month_records)

            return {
                "period": f"{now.strftime('%Y-%m')}",
                "current_spend_usd": round(current_spend, 4),
                "monthly_budget_usd": self.monthly_budget_usd,
                "budget_remaining_usd": round(self.monthly_budget_usd - current_spend, 4),
                "budget_utilization_pct": round(
                    (
                        (current_spend / self.monthly_budget_usd * 100)
                        if self.monthly_budget_usd > 0
                        else 0
                    ),
                    1,
                ),
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "avg_tokens_per_request": (
                    round(total_tokens / total_requests, 1) if total_requests > 0 else 0
                ),
                "avg_cost_per_request_usd": (
                    round(current_spend / total_requests, 6) if total_requests > 0 else 0
                ),
                "by_model": dict(by_model),
                "by_tenant": dict(by_tenant),
                "daily_trend": dict(sorted(daily.items())),
                "recent_alerts": [
                    {
                        "timestamp": a.timestamp,
                        "message": a.message,
                        "percentage": round(a.percentage * 100, 1),
                    }
                    for a in self._alerts[-10:]
                ],
            }

    def get_tenant_usage(self, tenant_id: str) -> dict[str, Any]:
        """Get usage breakdown for a specific tenant."""
        with self._lock:
            records = [r for r in self._records if r.tenant_id == tenant_id]
            total_cost = sum(r.estimated_cost_usd for r in records)
            total_tokens = sum(r.total_tokens for r in records)
            return {
                "tenant_id": tenant_id,
                "total_requests": len(records),
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
            }

    def reset_monthly_alert(self) -> None:
        """Reset the monthly alert flag (call at month boundary)."""
        with self._lock:
            self._alert_sent_this_period = False


# ── Singleton ────────────────────────────────────────────────────

_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    """Get the global CostTracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
