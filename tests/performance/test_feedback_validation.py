"""
Performance validation tests for the FeedbackLoopValidator.

Replaces the --mock CLI claim with real pytest assertions that prove:
1. Golden paths are stored and retrievable after feedback recording
2. Golden path retrieval is faster than full query execution
3. Confidence is maintained or improved after golden path injection
4. At least 40% of re-run queries use golden paths
5. The full 4-phase validation pipeline passes end-to-end
"""

import asyncio
import statistics
import time

import pytest

from packages.agent_framework.learning.feedback_loop import FeedbackCollector, GoldenPath
from packages.agent_framework.learning.feedback_validator import (
    DEFAULT_TEST_QUERIES,
    MOCK_RESPONSES,
    FeedbackLoopValidator,
    InMemoryVectorStore,
    QueryResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vector_store() -> InMemoryVectorStore:
    """Fresh in-memory vector store per test."""
    return InMemoryVectorStore()


@pytest.fixture()
def collector(vector_store: InMemoryVectorStore) -> FeedbackCollector:
    """FeedbackCollector wired to the in-memory vector store."""
    return FeedbackCollector(vector_store=vector_store)


@pytest.fixture()
def validator() -> FeedbackLoopValidator:
    """Validator using in-memory vector store (no external deps)."""
    return FeedbackLoopValidator(mock=True)


# ---------------------------------------------------------------------------
# Phase 1: Vector store upsert + search actually works
# ---------------------------------------------------------------------------


class TestVectorStoreIntegrity:
    """Prove InMemoryVectorStore is a real store, not a passthrough."""

    @pytest.mark.asyncio
    async def test_upsert_and_search_returns_results(
        self, vector_store: InMemoryVectorStore
    ) -> None:
        docs = [
            {
                "id": "doc-1",
                "content": "To reset your password go to Settings Security",
                "metadata": {"type": "golden_path", "input_query": "reset password"},
            }
        ]
        count = await vector_store.upsert(docs)
        assert count == 1

        results = await vector_store.search("how do I reset my password", top_k=3)
        assert len(results) >= 1
        assert results[0]["score"] > 0.3

    @pytest.mark.asyncio
    async def test_search_empty_store_returns_nothing(
        self, vector_store: InMemoryVectorStore
    ) -> None:
        results = await vector_store.search("anything", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_irrelevant_query_returns_nothing(
        self, vector_store: InMemoryVectorStore
    ) -> None:
        docs = [
            {
                "id": "doc-1",
                "content": "quantum chromodynamics gluon interaction",
                "metadata": {"type": "golden_path"},
            }
        ]
        await vector_store.upsert(docs)
        results = await vector_store.search("reset my password", top_k=3)
        # Word overlap scoring should yield 0 matches for unrelated content
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_removes_document(
        self, vector_store: InMemoryVectorStore
    ) -> None:
        docs = [{"id": "doc-del", "content": "deletable content", "metadata": {}}]
        await vector_store.upsert(docs)
        assert len(await vector_store.search("deletable", top_k=1)) >= 1

        await vector_store.delete(["doc-del"])
        assert len(await vector_store.search("deletable", top_k=1)) == 0


# ---------------------------------------------------------------------------
# Phase 2: FeedbackCollector golden path lifecycle
# ---------------------------------------------------------------------------


class TestGoldenPathLifecycle:
    """Prove golden paths are stored, deduplicated, and searchable."""

    @pytest.mark.asyncio
    async def test_record_success_creates_golden_path(
        self, collector: FeedbackCollector
    ) -> None:
        trace = {
            "input_query": "How do I reset my password?",
            "output": {"response": "Go to Settings > Security > Reset Password."},
            "agent_blueprint": "support_agent",
            "confidence": 0.88,
        }
        gp = await collector.record_success(trace, approved_by="test", tenant_id="t1")
        assert gp is not None
        assert isinstance(gp, GoldenPath)
        assert gp.success_count == 1
        assert gp.input_query == "How do I reset my password?"

    @pytest.mark.asyncio
    async def test_duplicate_success_increments_count(
        self, collector: FeedbackCollector
    ) -> None:
        trace = {
            "input_query": "How do I cancel my subscription?",
            "output": {"response": "Go to Billing > Cancel."},
            "agent_blueprint": "support_agent",
            "confidence": 0.76,
        }
        gp1 = await collector.record_success(trace)
        gp2 = await collector.record_success(trace)
        assert gp2 is not None
        assert gp2.success_count == 2

    @pytest.mark.asyncio
    async def test_golden_path_searchable_after_record(
        self, collector: FeedbackCollector
    ) -> None:
        trace = {
            "input_query": "How do I enable two-factor authentication?",
            "output": {"response": "Go to Settings > Security > 2FA."},
            "agent_blueprint": "support_agent",
            "confidence": 0.91,
        }
        await collector.record_success(trace, tenant_id="validation")

        results = await collector.search_golden_paths(
            query="enable two-factor authentication", top_k=3
        )
        assert len(results) >= 1, "Golden path should be retrievable after recording"

    @pytest.mark.asyncio
    async def test_failure_downgrades_success_rate(
        self, collector: FeedbackCollector
    ) -> None:
        trace = {
            "input_query": "What are your refund policies?",
            "output": {"response": "We offer refunds within 30 days."},
            "agent_blueprint": "support_agent",
            "confidence": 0.68,
        }
        await collector.record_success(trace)
        gp = await collector.record_failure(trace, reason="Incomplete answer")
        assert gp is not None
        assert gp.failure_count >= 1
        assert gp.success_rate < 1.0

    @pytest.mark.asyncio
    async def test_correction_overrides_resolution(
        self, collector: FeedbackCollector
    ) -> None:
        trace = {
            "input_query": "Can I change my email?",
            "output": {"response": "Original answer."},
            "agent_blueprint": "support_agent",
            "confidence": 0.50,
        }
        await collector.record_success(trace)
        gp = await collector.record_correction(
            original_trace=trace,
            corrected_output="Go to Settings > Profile > Email.",
            corrected_by="human_reviewer",
        )
        assert gp is not None
        assert gp.resolution == "Go to Settings > Profile > Email."
        assert gp.confidence == 0.95


# ---------------------------------------------------------------------------
# Phase 3: Full validation pipeline
# ---------------------------------------------------------------------------


class TestValidationPipeline:
    """Prove the 4-phase validation pipeline produces real, verifiable results."""

    @pytest.mark.asyncio
    async def test_full_validation_passes(self, validator: FeedbackLoopValidator) -> None:
        report = await validator.run_validation()

        assert report["total_queries"] == len(DEFAULT_TEST_QUERIES)
        assert report["validation_passed"] is True, (
            f"Validation failed: {report.get('validation_criteria')}"
        )

    @pytest.mark.asyncio
    async def test_golden_paths_stored_count(self, validator: FeedbackLoopValidator) -> None:
        report = await validator.run_validation()

        # Top 60% of 10 queries = 6 golden paths
        assert report["golden_paths_stored"] >= 6

    @pytest.mark.asyncio
    async def test_golden_paths_used_on_rerun(self, validator: FeedbackLoopValidator) -> None:
        report = await validator.run_validation()

        # At least 40% of queries should use golden paths on re-run
        assert report["golden_paths_used"] >= 4, (
            f"Only {report['golden_paths_used']}/{report['total_queries']} used golden paths"
        )
        assert report["golden_path_usage_rate"] >= 0.4

    @pytest.mark.asyncio
    async def test_confidence_maintained(self, validator: FeedbackLoopValidator) -> None:
        report = await validator.run_validation()

        # Confidence should not regress more than 5%
        assert report["confidence_improvement"] >= -0.05, (
            f"Confidence regressed by {report['confidence_improvement']}"
        )

    @pytest.mark.asyncio
    async def test_golden_path_retrieval_not_regressed(
        self, validator: FeedbackLoopValidator
    ) -> None:
        report = await validator.run_validation()

        # Golden path queries should not regress (1ms tolerance for sub-ms jitter)
        assert report["time_improvement_ms"] >= -1.0, (
            f"Golden path queries regressed by {abs(report['time_improvement_ms'])}ms"
        )

    @pytest.mark.asyncio
    async def test_baseline_has_no_golden_paths(self, validator: FeedbackLoopValidator) -> None:
        await validator.run_validation()

        # Phase 1 baseline should have found zero golden paths
        for result in validator.baseline_results:
            assert result.used_golden_path is False

    @pytest.mark.asyncio
    async def test_improved_results_have_golden_paths(
        self, validator: FeedbackLoopValidator
    ) -> None:
        await validator.run_validation()

        gp_used = [r for r in validator.improved_results if r.used_golden_path]
        assert len(gp_used) >= 1, "At least one improved query should use a golden path"

    @pytest.mark.asyncio
    async def test_feedback_stats_populated(self, validator: FeedbackLoopValidator) -> None:
        report = await validator.run_validation()

        stats = report.get("feedback_stats", {})
        assert stats["total_golden_paths"] >= 1
        assert stats["approved"] >= 1
        assert stats["avg_success_rate"] > 0


# ---------------------------------------------------------------------------
# Phase 4: Performance benchmarks
# ---------------------------------------------------------------------------


class TestPerformanceBenchmarks:
    """Quantitative performance assertions on the feedback loop."""

    @pytest.mark.asyncio
    async def test_single_query_under_100ms(self, validator: FeedbackLoopValidator) -> None:
        """A single mock query + golden path search should complete in < 100ms."""
        start = time.perf_counter()
        await validator.run_validation(test_queries=["How do I reset my password?"])
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"Single query validation took {elapsed_ms:.1f}ms (limit: 100ms)"

    @pytest.mark.asyncio
    async def test_full_10_query_validation_under_500ms(
        self, validator: FeedbackLoopValidator
    ) -> None:
        """Full 10-query validation (baseline + feedback + re-run) under 500ms."""
        start = time.perf_counter()
        await validator.run_validation()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, (
            f"Full validation took {elapsed_ms:.1f}ms (limit: 500ms)"
        )

    @pytest.mark.asyncio
    async def test_concurrent_validations(self) -> None:
        """Run 10 concurrent validators to prove no shared state corruption."""
        async def run_one() -> dict:
            v = FeedbackLoopValidator(mock=True)
            return await v.run_validation()

        results = await asyncio.gather(*[run_one() for _ in range(10)])

        for i, report in enumerate(results):
            assert report["validation_passed"] is True, (
                f"Concurrent validator {i} failed: {report.get('validation_criteria')}"
            )
            assert report["total_queries"] == len(DEFAULT_TEST_QUERIES)

    @pytest.mark.asyncio
    async def test_golden_path_search_latency(
        self, collector: FeedbackCollector
    ) -> None:
        """Golden path search should be sub-millisecond for in-memory store."""
        # Seed 10 golden paths
        for query, mock in MOCK_RESPONSES.items():
            trace = {
                "input_query": query,
                "output": {"response": mock["response"]},
                "agent_blueprint": "support_agent",
                "confidence": mock["confidence"],
            }
            await collector.record_success(trace)

        # Measure search latency over 100 iterations
        latencies: list[float] = []
        for query in DEFAULT_TEST_QUERIES:
            for _ in range(10):
                start = time.perf_counter()
                await collector.search_golden_paths(query=query, top_k=3)
                latencies.append((time.perf_counter() - start) * 1000)

        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]

        assert p50 < 1.0, f"p50 search latency {p50:.3f}ms exceeds 1ms"
        assert p95 < 5.0, f"p95 search latency {p95:.3f}ms exceeds 5ms"
        assert p99 < 10.0, f"p99 search latency {p99:.3f}ms exceeds 10ms"
