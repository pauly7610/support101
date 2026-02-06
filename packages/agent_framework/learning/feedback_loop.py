"""
Feedback Loop for Continuous Agent Learning.

Captures HITL outcomes (approvals, rejections, corrections) and customer
signals (CSAT, ticket resolution) as "golden paths" in the vector store.
Future agent RAG queries automatically retrieve these proven resolutions.

No new dependencies required — uses existing VectorStoreService and EventBus.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class FeedbackOutcome(StrEnum):
    """Outcome types for feedback signals."""

    APPROVED = "approved"
    REJECTED = "rejected"
    CORRECTED = "corrected"
    POSITIVE_CSAT = "positive_csat"
    NEGATIVE_CSAT = "negative_csat"
    TICKET_RESOLVED = "ticket_resolved"
    TICKET_REOPENED = "ticket_reopened"


@dataclass
class GoldenPath:
    """A proven resolution trace stored for future RAG retrieval."""

    id: str = field(default_factory=lambda: f"gp-{uuid4().hex[:12]}")
    agent_blueprint: str = ""
    category: str = ""
    input_query: str = ""
    resolution: str = ""
    steps_taken: list[str] = field(default_factory=list)
    articles_used: list[str] = field(default_factory=list)
    confidence: float = 0.0
    outcome: FeedbackOutcome = FeedbackOutcome.APPROVED
    approved_by: str | None = None
    tenant_id: str = ""
    success_count: int = 1
    failure_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def to_document(self) -> dict[str, Any]:
        """Convert to a document suitable for vector store upsert."""
        content = (
            f"Resolution for: {self.input_query}\n\n"
            f"Steps: {' → '.join(self.steps_taken)}\n\n"
            f"Answer: {self.resolution}"
        )
        return {
            "id": self.id,
            "content": content,
            "metadata": {
                "type": "golden_path",
                "agent_blueprint": self.agent_blueprint,
                "category": self.category,
                "input_query": self.input_query,
                "resolution": self.resolution[:2000],
                "steps_taken": json.dumps(self.steps_taken),
                "articles_used": json.dumps(self.articles_used),
                "confidence": self.confidence,
                "outcome": self.outcome.value,
                "approved_by": self.approved_by or "",
                "tenant_id": self.tenant_id,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "success_rate": self.success_rate,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            },
        }

    def fingerprint(self) -> str:
        """Generate a content fingerprint for deduplication."""
        key = f"{self.agent_blueprint}:{self.category}:{self.input_query[:200]}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]


class FeedbackCollector:
    """
    Collects feedback signals and writes golden paths to the vector store.

    Subscribes to EventBus for HITL outcomes and provides methods for
    external feedback (CSAT, ticket resolution webhooks).

    Usage:
        collector = FeedbackCollector(vector_store, event_bus, audit_logger)
        await collector.start()

        # Automatic: HITL approvals trigger golden path creation
        # Manual: record external signals
        await collector.record_success(trace, reviewer_id, tenant_id)
    """

    GOLDEN_PATH_NAMESPACE = "golden_paths"

    def __init__(
        self,
        vector_store: Any | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
        activity_graph: Any | None = None,
    ) -> None:
        self._vs = vector_store
        self._event_bus = event_bus
        self._audit_logger = audit_logger
        self._activity_graph = activity_graph
        self._golden_paths: dict[str, GoldenPath] = {}
        self._started = False

    @property
    def available(self) -> bool:
        return self._vs is not None

    async def start(self) -> None:
        """Subscribe to EventBus for HITL outcome events."""
        if self._started or self._event_bus is None:
            return
        try:
            from ..realtime.events import EventType

            self._event_bus.subscribe(EventType.HITL_REQUEST_RESPONDED, self._on_hitl_responded)
            self._started = True
            logger.info("FeedbackCollector: subscribed to HITL events")
        except Exception as e:
            logger.warning("FeedbackCollector: failed to subscribe: %s", e)

    async def _on_hitl_responded(self, event: Any) -> None:
        """Handle HITL response events from EventBus."""
        data = event.data if hasattr(event, "data") else {}
        decision = data.get("decision", "")
        request_data = data.get("request", {})
        reviewer_id = data.get("reviewer_id", "")
        tenant_id = event.tenant_id if hasattr(event, "tenant_id") else data.get("tenant_id", "")

        trace = self._extract_trace(request_data)

        if decision == "approve":
            await self.record_success(
                trace=trace,
                approved_by=reviewer_id,
                tenant_id=tenant_id,
            )
        elif decision == "reject":
            await self.record_failure(
                trace=trace,
                reason=data.get("reason", ""),
                tenant_id=tenant_id,
            )
        elif decision in ("modify", "edit"):
            await self.record_correction(
                original_trace=trace,
                corrected_output=data.get("edited_response", data.get("response", "")),
                corrected_by=reviewer_id,
                tenant_id=tenant_id,
            )

    def _extract_trace(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Extract execution trace from HITL request data."""
        context = request_data.get("context", {})
        agent_state = request_data.get("agent_state_snapshot", {})
        return {
            "input_query": context.get("input_data", {}).get("query", ""),
            "steps": [s.get("action", "") for s in agent_state.get("intermediate_steps", [])],
            "output": context.get("output_data", {}),
            "agent_blueprint": request_data.get("metadata", {}).get("blueprint", ""),
            "category": request_data.get("metadata", {}).get("category", "general"),
            "articles_used": context.get("sources", []),
            "confidence": context.get("confidence", 0.0),
        }

    async def record_success(
        self,
        trace: dict[str, Any],
        approved_by: str = "",
        tenant_id: str = "",
    ) -> GoldenPath | None:
        """Record a successful resolution as a golden path."""
        output = trace.get("output", {})
        resolution = output.get("response", "") if isinstance(output, dict) else str(output)

        gp = GoldenPath(
            agent_blueprint=trace.get("agent_blueprint", ""),
            category=trace.get("category", "general"),
            input_query=trace.get("input_query", ""),
            resolution=resolution,
            steps_taken=trace.get("steps", []),
            articles_used=trace.get("articles_used", []),
            confidence=trace.get("confidence", 0.0),
            outcome=FeedbackOutcome.APPROVED,
            approved_by=approved_by,
            tenant_id=tenant_id,
        )

        existing = self._find_existing(gp)
        if existing:
            existing.success_count += 1
            existing.updated_at = datetime.utcnow().isoformat()
            if gp.confidence > existing.confidence:
                existing.confidence = gp.confidence
                existing.resolution = gp.resolution
            gp = existing

        self._golden_paths[gp.fingerprint()] = gp

        await self._upsert_to_vector_store(gp)
        await self._update_graph(gp, success=True)
        await self._log_feedback(gp, "success")

        logger.info(
            "FeedbackCollector: recorded success for '%s' (count=%d)",
            gp.input_query[:50],
            gp.success_count,
        )
        return gp

    async def record_failure(
        self,
        trace: dict[str, Any],
        reason: str = "",
        tenant_id: str = "",
    ) -> GoldenPath | None:
        """Record a failed resolution to downrank or flag gaps."""
        output = trace.get("output", {})
        resolution = output.get("response", "") if isinstance(output, dict) else str(output)

        gp = GoldenPath(
            agent_blueprint=trace.get("agent_blueprint", ""),
            category=trace.get("category", "general"),
            input_query=trace.get("input_query", ""),
            resolution=resolution,
            steps_taken=trace.get("steps", []),
            articles_used=trace.get("articles_used", []),
            confidence=trace.get("confidence", 0.0),
            outcome=FeedbackOutcome.REJECTED,
            tenant_id=tenant_id,
        )

        existing = self._find_existing(gp)
        if existing:
            existing.failure_count += 1
            existing.updated_at = datetime.utcnow().isoformat()
            gp = existing
            if gp.success_rate < 0.3:
                await self._remove_from_vector_store(gp)
                logger.info("FeedbackCollector: removed low-success golden path '%s'", gp.id)
        else:
            gp.failure_count = 1
            gp.success_count = 0

        self._golden_paths[gp.fingerprint()] = gp
        await self._update_graph(gp, success=False)
        await self._log_feedback(gp, "failure", reason=reason)

        logger.info(
            "FeedbackCollector: recorded failure for '%s' (rate=%.2f)",
            gp.input_query[:50],
            gp.success_rate,
        )
        return gp

    async def record_correction(
        self,
        original_trace: dict[str, Any],
        corrected_output: str,
        corrected_by: str = "",
        tenant_id: str = "",
    ) -> GoldenPath | None:
        """Record a human-corrected resolution as the golden path."""
        gp = GoldenPath(
            agent_blueprint=original_trace.get("agent_blueprint", ""),
            category=original_trace.get("category", "general"),
            input_query=original_trace.get("input_query", ""),
            resolution=corrected_output,
            steps_taken=original_trace.get("steps", []),
            articles_used=original_trace.get("articles_used", []),
            confidence=0.95,
            outcome=FeedbackOutcome.CORRECTED,
            approved_by=corrected_by,
            tenant_id=tenant_id,
        )

        existing = self._find_existing(gp)
        if existing:
            existing.resolution = corrected_output
            existing.confidence = 0.95
            existing.success_count += 1
            existing.outcome = FeedbackOutcome.CORRECTED
            existing.updated_at = datetime.utcnow().isoformat()
            gp = existing

        self._golden_paths[gp.fingerprint()] = gp

        await self._upsert_to_vector_store(gp)
        await self._update_graph(gp, success=True)
        await self._log_feedback(gp, "correction")

        logger.info(
            "FeedbackCollector: recorded correction for '%s' by %s",
            gp.input_query[:50],
            corrected_by,
        )
        return gp

    async def record_csat(
        self,
        ticket_id: str,
        score: float,
        trace: dict[str, Any],
        tenant_id: str = "",
    ) -> GoldenPath | None:
        """Record customer satisfaction signal."""
        if score >= 4.0:
            return await self.record_success(trace=trace, tenant_id=tenant_id)
        elif score <= 2.0:
            return await self.record_failure(
                trace=trace, reason=f"Low CSAT: {score}", tenant_id=tenant_id
            )
        return None

    async def search_golden_paths(
        self,
        query: str,
        tenant_id: str = "",
        top_k: int = 3,
        min_success_rate: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Search for relevant golden paths for a query."""
        if not self.available:
            return []

        results = await self._vs.search(
            query=query,
            top_k=top_k * 2,
            filter_metadata=(
                {"type": "golden_path", "tenant_id": tenant_id}
                if tenant_id
                else {"type": "golden_path"}
            ),
        )

        filtered = []
        for r in results:
            meta = r if isinstance(r, dict) else {}
            sr = meta.get("success_rate", meta.get("metadata", {}).get("success_rate", 1.0))
            if sr >= min_success_rate:
                filtered.append(r)
            if len(filtered) >= top_k:
                break

        return filtered

    def _find_existing(self, gp: GoldenPath) -> GoldenPath | None:
        """Find an existing golden path by fingerprint."""
        return self._golden_paths.get(gp.fingerprint())

    async def _upsert_to_vector_store(self, gp: GoldenPath) -> None:
        """Write golden path to vector store."""
        if not self.available:
            return
        try:
            doc = gp.to_document()
            await self._vs.upsert([doc])
        except Exception as e:
            logger.warning("FeedbackCollector: vector store upsert failed: %s", e)

    async def _remove_from_vector_store(self, gp: GoldenPath) -> None:
        """Remove a low-performing golden path from vector store."""
        if not self.available:
            return
        try:
            await self._vs.delete([gp.id])
        except Exception as e:
            logger.warning("FeedbackCollector: vector store delete failed: %s", e)

    async def _update_graph(self, gp: GoldenPath, success: bool) -> None:
        """Update the activity graph with resolution data."""
        if self._activity_graph is None:
            return
        try:
            await self._activity_graph.record_resolution(
                golden_path_id=gp.id,
                agent_blueprint=gp.agent_blueprint,
                category=gp.category,
                input_query=gp.input_query,
                steps=gp.steps_taken,
                articles=gp.articles_used,
                success=success,
                confidence=gp.confidence,
                tenant_id=gp.tenant_id,
            )
        except Exception as e:
            logger.debug("FeedbackCollector: graph update failed: %s", e)

    async def _log_feedback(self, gp: GoldenPath, outcome_type: str, reason: str = "") -> None:
        """Log feedback event to audit logger."""
        if self._audit_logger is None:
            return
        try:
            from ..governance.audit import AuditEventType

            await self._audit_logger.log_agent_event(
                event_type=AuditEventType.DATA_MODIFIED,
                agent_id=gp.agent_blueprint,
                tenant_id=gp.tenant_id,
                details={
                    "feedback_type": outcome_type,
                    "golden_path_id": gp.id,
                    "category": gp.category,
                    "input_query": gp.input_query[:200],
                    "success_count": gp.success_count,
                    "failure_count": gp.failure_count,
                    "success_rate": gp.success_rate,
                    "reason": reason,
                },
            )
        except Exception as e:
            logger.debug("FeedbackCollector: audit log failed: %s", e)

    def get_stats(self) -> dict[str, Any]:
        """Get feedback loop statistics."""
        total = len(self._golden_paths)
        approved = sum(
            1 for gp in self._golden_paths.values() if gp.outcome == FeedbackOutcome.APPROVED
        )
        corrected = sum(
            1 for gp in self._golden_paths.values() if gp.outcome == FeedbackOutcome.CORRECTED
        )
        rejected = sum(
            1 for gp in self._golden_paths.values() if gp.outcome == FeedbackOutcome.REJECTED
        )
        avg_rate = (
            sum(gp.success_rate for gp in self._golden_paths.values()) / total if total > 0 else 0.0
        )
        return {
            "total_golden_paths": total,
            "approved": approved,
            "corrected": corrected,
            "rejected": rejected,
            "avg_success_rate": round(avg_rate, 3),
        }
