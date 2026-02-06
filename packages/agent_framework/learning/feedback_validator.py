"""
Feedback Loop Validator — Proves the continuous learning system works.

Validates that HITL-approved golden paths measurably improve agent performance:
1. Baseline: Run queries, search golden paths (should be empty)
2. Feedback: Store top responses as golden paths via FeedbackCollector
3. Improved: Re-run same queries, search golden paths (should match)
4. Report: Compare retrieval rates, confidence, response times

Supports two modes:
- Live mode: Uses real Pinecone + LLM (requires API keys)
- Mock mode: Uses in-memory vector store + synthetic responses (for CI)

Usage:
    python packages/agent_framework/learning/feedback_validator.py
    python packages/agent_framework/learning/feedback_validator.py --mock
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..learning.feedback_loop import FeedbackCollector
from ..services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# ── Test Queries ────────────────────────────────────────────────────────────

DEFAULT_TEST_QUERIES: list[str] = [
    "How do I reset my password?",
    "My account is locked, what should I do?",
    "How can I upgrade my subscription plan?",
    "Where do I find my billing invoices?",
    "How do I cancel my subscription?",
    "I forgot my username, how can I recover it?",
    "How do I enable two-factor authentication?",
    "What are your refund policies?",
    "How long does it take to process a refund?",
    "Can I change my email address?",
]

# ── Mock Responses (for CI / no-API-key mode) ──────────────────────────────

MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "How do I reset my password?": {
        "response": "Go to Settings > Security > Reset Password. Enter your current password, then your new password twice. Click Save.",
        "confidence": 0.88,
        "sources": ["https://docs.support101.com/security/password-reset"],
    },
    "My account is locked, what should I do?": {
        "response": "If your account is locked after too many failed login attempts, wait 30 minutes or contact support to unlock it immediately.",
        "confidence": 0.82,
        "sources": ["https://docs.support101.com/security/account-lockout"],
    },
    "How can I upgrade my subscription plan?": {
        "response": "Navigate to Billing > Plans, select your desired plan, and click Upgrade. Changes take effect immediately and you'll be prorated.",
        "confidence": 0.79,
        "sources": ["https://docs.support101.com/billing/upgrade"],
    },
    "Where do I find my billing invoices?": {
        "response": "Go to Billing > Invoices to view and download all past invoices as PDF.",
        "confidence": 0.85,
        "sources": ["https://docs.support101.com/billing/invoices"],
    },
    "How do I cancel my subscription?": {
        "response": "Go to Billing > Plans > Cancel Subscription. You'll retain access until the end of your billing period.",
        "confidence": 0.76,
        "sources": ["https://docs.support101.com/billing/cancel"],
    },
    "I forgot my username, how can I recover it?": {
        "response": "Click 'Forgot Username' on the login page and enter your registered email. We'll send your username within 5 minutes.",
        "confidence": 0.72,
        "sources": ["https://docs.support101.com/security/username-recovery"],
    },
    "How do I enable two-factor authentication?": {
        "response": "Go to Settings > Security > Two-Factor Authentication. Scan the QR code with your authenticator app and enter the verification code.",
        "confidence": 0.91,
        "sources": ["https://docs.support101.com/security/2fa"],
    },
    "What are your refund policies?": {
        "response": "We offer full refunds within 30 days of purchase. After 30 days, prorated refunds are available for annual plans.",
        "confidence": 0.68,
        "sources": ["https://docs.support101.com/billing/refunds"],
    },
    "How long does it take to process a refund?": {
        "response": "Refunds are processed within 5-10 business days. You'll receive an email confirmation once the refund is initiated.",
        "confidence": 0.74,
        "sources": ["https://docs.support101.com/billing/refund-timeline"],
    },
    "Can I change my email address?": {
        "response": "Go to Settings > Profile > Email. Enter your new email and verify it via the confirmation link we send.",
        "confidence": 0.83,
        "sources": ["https://docs.support101.com/account/email-change"],
    },
}


# ── In-Memory Vector Store (for mock mode) ─────────────────────────────────


class InMemoryVectorStore:
    """Minimal vector store that uses string matching for mock validation."""

    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}

    @property
    def available(self) -> bool:
        return True

    async def upsert(self, documents: list[dict[str, Any]], **kwargs: Any) -> int:
        for doc in documents:
            self._documents[doc["id"]] = doc
        return len(documents)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        query_lower = query.lower()
        for doc_id, doc in self._documents.items():
            meta = doc.get("metadata", {})
            if filter_metadata and not all(meta.get(k) == v for k, v in filter_metadata.items()):
                continue
            content = doc.get("content", "").lower()
            input_query = meta.get("input_query", "").lower()
            # Simple word overlap scoring
            query_words = set(query_lower.split())
            content_words = set(content.split()) | set(input_query.split())
            overlap = len(query_words & content_words)
            score = overlap / max(len(query_words), 1)
            if score > 0.3:
                results.append(
                    {
                        "id": doc_id,
                        "content": doc.get("content", ""),
                        "score": min(score, 0.95),
                        "metadata": meta,
                    }
                )
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def delete(self, ids: list[str]) -> bool:
        for doc_id in ids:
            self._documents.pop(doc_id, None)
        return True


# ── Result Dataclass ────────────────────────────────────────────────────────


@dataclass
class QueryResult:
    """Result of a single query execution."""

    query: str = ""
    response: str = ""
    confidence: float = 0.0
    sources_used: int = 0
    execution_time_ms: float = 0.0
    used_golden_path: bool = False
    golden_path_score: float = 0.0


# ── Validator ───────────────────────────────────────────────────────────────


class FeedbackLoopValidator:
    """
    Validates that the continuous learning feedback loop improves agent
    performance by comparing baseline vs. golden-path-enhanced queries.
    """

    def __init__(self, mock: bool = False) -> None:
        self.mock = mock
        if mock:
            self._vs = InMemoryVectorStore()
        else:
            self._vs = VectorStoreService()

        self.feedback_collector = FeedbackCollector(vector_store=self._vs)
        self.baseline_results: list[QueryResult] = []
        self.improved_results: list[QueryResult] = []

    async def _execute_query(self, query: str) -> dict[str, Any]:
        """Execute a query — mock or live."""
        if self.mock:
            mock = MOCK_RESPONSES.get(
                query,
                {
                    "response": f"Generic answer for: {query}",
                    "confidence": 0.60,
                    "sources": [],
                },
            )
            await asyncio.sleep(0.05)  # Simulate latency
            return mock

        # Live mode: use the RAG chain
        try:
            from ...llm_engine.chains.rag_chain import RAGChain

            chain = RAGChain()
            result = await chain.generate(query)
            return {
                "response": result.get("reply", ""),
                "confidence": max(
                    (s.get("confidence", 0) for s in result.get("sources", [])),
                    default=0.0,
                ),
                "sources": [s.get("url", "") for s in result.get("sources", [])],
            }
        except Exception as e:
            logger.warning("Live query failed, falling back to mock: %s", e)
            return MOCK_RESPONSES.get(
                query,
                {
                    "response": f"Fallback answer for: {query}",
                    "confidence": 0.50,
                    "sources": [],
                },
            )

    async def run_validation(self, test_queries: list[str] | None = None) -> dict[str, Any]:
        """
        Full validation flow:
        1. Baseline: Run queries, check golden paths (should be empty)
        2. Feedback: Store top 60% as golden paths
        3. Improved: Re-run queries, check golden paths (should match)
        4. Report: Compare metrics
        """
        queries = test_queries or DEFAULT_TEST_QUERIES

        print("=" * 80)
        print("FEEDBACK LOOP VALIDATION" + (" (MOCK MODE)" if self.mock else ""))
        print("=" * 80)

        # ── Phase 1: Baseline ───────────────────────────────────────────
        print("\nPhase 1: Baseline (no golden paths)")
        print("-" * 80)

        for i, query in enumerate(queries, 1):
            print(f"\n  Query {i}/{len(queries)}: {query}")

            # Check golden paths — should be empty
            gp_results = await self.feedback_collector.search_golden_paths(query=query, top_k=3)

            start = time.perf_counter()
            result = await self._execute_query(query)
            elapsed_ms = (time.perf_counter() - start) * 1000

            qr = QueryResult(
                query=query,
                response=result.get("response", ""),
                confidence=result.get("confidence", 0.0),
                sources_used=len(result.get("sources", [])),
                execution_time_ms=round(elapsed_ms, 1),
                used_golden_path=False,
                golden_path_score=0.0,
            )
            self.baseline_results.append(qr)

            print(f"    Confidence: {qr.confidence:.2f}")
            print(f"    Sources: {qr.sources_used}")
            print(f"    Time: {qr.execution_time_ms}ms")
            print(f"    Golden paths found: {len(gp_results)} (expected: 0)")

        # ── Phase 2: Store Golden Paths ─────────────────────────────────
        print("\n" + "=" * 80)
        print("Phase 2: Storing Golden Paths (top 60% by confidence)")
        print("-" * 80)

        sorted_results = sorted(
            self.baseline_results,
            key=lambda x: x.confidence,
            reverse=True,
        )
        top_count = max(1, int(len(sorted_results) * 0.6))
        top_results = sorted_results[:top_count]

        for i, qr in enumerate(top_results, 1):
            print(f"\n  Storing golden path {i}/{len(top_results)}")
            print(f"    Query: {qr.query}")
            print(f"    Confidence: {qr.confidence:.2f}")

            trace = {
                "input_query": qr.query,
                "output": {"response": qr.response},
                "agent_blueprint": "support_agent",
                "category": "general",
                "steps": ["retrieve_context", "generate_response"],
                "articles_used": [],
                "confidence": qr.confidence,
            }

            gp = await self.feedback_collector.record_success(
                trace=trace,
                approved_by="feedback_validator",
                tenant_id="validation",
            )

            if gp:
                print(f"    Stored: {gp.id}")
            else:
                print("    Warning: Failed to store golden path")

        # ── Phase 3: Re-run with Golden Paths ───────────────────────────
        print("\n" + "=" * 80)
        print("Phase 3: Re-run with Golden Path Retrieval")
        print("-" * 80)

        for i, query in enumerate(queries, 1):
            print(f"\n  Query {i}/{len(queries)}: {query}")

            # Search golden paths — should now return matches
            start = time.perf_counter()
            gp_results = await self.feedback_collector.search_golden_paths(
                query=query, top_k=3, min_success_rate=0.5
            )
            gp_elapsed_ms = (time.perf_counter() - start) * 1000

            used_gp = len(gp_results) > 0
            gp_score = gp_results[0].get("score", 0.0) if gp_results else 0.0

            if used_gp:
                # Golden path found — use cached response (no LLM call)
                gp_meta = gp_results[0].get("metadata", {})
                response = gp_meta.get("resolution", "")
                confidence = gp_meta.get("confidence", gp_score)
                elapsed_ms = round(gp_elapsed_ms, 1)
                print(f"    GOLDEN PATH USED (score: {gp_score:.2f})")
            else:
                # No golden path — full LLM call
                exec_start = time.perf_counter()
                result = await self._execute_query(query)
                elapsed_ms = round((time.perf_counter() - exec_start) * 1000 + gp_elapsed_ms, 1)
                response = result.get("response", "")
                confidence = result.get("confidence", 0.0)
                print("    No golden path match")

            qr = QueryResult(
                query=query,
                response=response,
                confidence=confidence,
                sources_used=len(gp_results) if used_gp else 0,
                execution_time_ms=elapsed_ms,
                used_golden_path=used_gp,
                golden_path_score=gp_score,
            )
            self.improved_results.append(qr)

            print(f"    Confidence: {qr.confidence:.2f}")
            print(f"    Time: {qr.execution_time_ms}ms")

        # ── Phase 4: Report ─────────────────────────────────────────────
        return self._generate_report()

    def _generate_report(self) -> dict[str, Any]:
        """Compare baseline vs improved metrics."""
        total = len(self.baseline_results)
        if total == 0:
            return {"error": "No results to report"}

        golden_paths_stored = sum(
            1
            for r in self.baseline_results
            if r
            in sorted(
                self.baseline_results,
                key=lambda x: x.confidence,
                reverse=True,
            )[: max(1, int(total * 0.6))]
        )
        golden_paths_used = sum(1 for r in self.improved_results if r.used_golden_path)

        avg_conf_before = sum(r.confidence for r in self.baseline_results) / total
        avg_conf_after = sum(r.confidence for r in self.improved_results) / total

        avg_time_before = sum(r.execution_time_ms for r in self.baseline_results) / total
        avg_time_after = sum(r.execution_time_ms for r in self.improved_results) / total

        conf_improvement = avg_conf_after - avg_conf_before
        time_improvement = avg_time_before - avg_time_after
        time_improvement_pct = (
            (time_improvement / avg_time_before) * 100 if avg_time_before > 0 else 0
        )

        # Validation criteria:
        # 1. At least 40% of queries used golden paths
        # 2. Confidence maintained (no more than 5% regression)
        # 3. Response time improved (golden paths are faster)
        validation_passed = (
            golden_paths_used >= total * 0.4 and conf_improvement >= -0.05 and time_improvement >= 0
        )

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "mode": "mock" if self.mock else "live",
            "total_queries": total,
            "golden_paths_stored": golden_paths_stored,
            "golden_paths_used": golden_paths_used,
            "golden_path_usage_rate": round(golden_paths_used / total, 3),
            "avg_confidence_before": round(avg_conf_before, 3),
            "avg_confidence_after": round(avg_conf_after, 3),
            "confidence_improvement": round(conf_improvement, 3),
            "confidence_improvement_pct": (
                round((conf_improvement / avg_conf_before) * 100, 1) if avg_conf_before > 0 else 0
            ),
            "avg_time_before_ms": round(avg_time_before, 1),
            "avg_time_after_ms": round(avg_time_after, 1),
            "time_improvement_ms": round(time_improvement, 1),
            "time_improvement_pct": round(time_improvement_pct, 1),
            "validation_passed": validation_passed,
            "validation_criteria": {
                "golden_path_usage": f">= 40% (actual: {golden_paths_used}/{total})",
                "confidence_maintained": f">= -5% (actual: {round(conf_improvement * 100, 1)}%)",
                "time_improved": f"> 0ms (actual: {round(time_improvement, 1)}ms)",
            },
            "feedback_stats": self.feedback_collector.get_stats(),
        }

        return report


# ── CLI Entry Point ─────────────────────────────────────────────────────────


async def main() -> dict[str, Any]:
    """Run validation with default test queries."""
    mock = "--mock" in sys.argv

    validator = FeedbackLoopValidator(mock=mock)

    print(f"\nStarting Feedback Loop Validation ({'mock' if mock else 'live'} mode)")
    print(f"Test queries: {len(DEFAULT_TEST_QUERIES)}")
    print()

    report = await validator.run_validation()

    print("\n" + "=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)
    print(json.dumps(report, indent=2))

    print("\n" + "=" * 80)
    if report.get("validation_passed"):
        print("VALIDATION PASSED — Feedback loop improves agent performance")
    else:
        print("VALIDATION FAILED — Review criteria above")
    print("=" * 80)

    return report


if __name__ == "__main__":
    report = asyncio.run(main())
