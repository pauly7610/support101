"""
Unit tests for Human-in-the-Loop components.

Tests:
- HITLQueue request management
- Priority ordering
- SLA tracking
- Request lifecycle
"""

import pytest
from datetime import datetime, timedelta

from packages.agent_framework.hitl.queue import (
    HITLQueue,
    HITLRequest,
    HITLRequestStatus,
    HITLRequestType,
    HITLPriority,
)


class TestHITLQueue:
    """Tests for HITLQueue."""

    def setup_method(self):
        self.queue = HITLQueue()

    @pytest.mark.asyncio
    async def test_enqueue_request(self):
        request = await self.queue.enqueue(
            request_type=HITLRequestType.REVIEW,
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Test Request",
            description="Test description",
            priority=HITLPriority.MEDIUM,
        )
        
        assert request.request_id is not None
        assert request.status == HITLRequestStatus.PENDING
        assert request.priority == HITLPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_get_request(self):
        request = await self.queue.enqueue(
            request_type=HITLRequestType.APPROVAL,
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Approval Request",
            description="Need approval",
        )
        
        retrieved = self.queue.get_request(request.request_id)
        assert retrieved is not None
        assert retrieved.request_id == request.request_id

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        await self.queue.enqueue(
            request_type=HITLRequestType.REVIEW,
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Low Priority",
            description="",
            priority=HITLPriority.LOW,
        )
        await self.queue.enqueue(
            request_type=HITLRequestType.REVIEW,
            agent_id="a2",
            tenant_id="t1",
            execution_id="e2",
            title="Critical Priority",
            description="",
            priority=HITLPriority.CRITICAL,
        )
        await self.queue.enqueue(
            request_type=HITLRequestType.REVIEW,
            agent_id="a3",
            tenant_id="t1",
            execution_id="e3",
            title="High Priority",
            description="",
            priority=HITLPriority.HIGH,
        )
        
        pending = self.queue.get_pending()
        assert pending[0].priority == HITLPriority.CRITICAL
        assert pending[1].priority == HITLPriority.HIGH
        assert pending[2].priority == HITLPriority.LOW

    @pytest.mark.asyncio
    async def test_assign_request(self):
        request = await self.queue.enqueue(
            request_type=HITLRequestType.REVIEW,
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Test",
            description="",
        )
        
        success = self.queue.assign(request.request_id, "reviewer_1")
        assert success is True
        
        updated = self.queue.get_request(request.request_id)
        assert updated.status == HITLRequestStatus.ASSIGNED
        assert updated.assigned_to == "reviewer_1"

    @pytest.mark.asyncio
    async def test_respond_to_request(self):
        request = await self.queue.enqueue(
            request_type=HITLRequestType.APPROVAL,
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Approval",
            description="",
        )
        
        success = await self.queue.respond(
            request.request_id,
            {"decision": "approve", "comment": "Looks good"},
            "reviewer_1",
        )
        assert success is True
        
        updated = self.queue.get_request(request.request_id)
        assert updated.status == HITLRequestStatus.COMPLETED
        assert updated.response["decision"] == "approve"

    @pytest.mark.asyncio
    async def test_cancel_request(self):
        request = await self.queue.enqueue(
            request_type=HITLRequestType.REVIEW,
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Test",
            description="",
        )
        
        success = self.queue.cancel(request.request_id, "No longer needed")
        assert success is True
        
        updated = self.queue.get_request(request.request_id)
        assert updated.status == HITLRequestStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_queue_stats(self):
        await self.queue.enqueue(
            request_type=HITLRequestType.REVIEW,
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Test 1",
            description="",
            priority=HITLPriority.HIGH,
        )
        await self.queue.enqueue(
            request_type=HITLRequestType.REVIEW,
            agent_id="a2",
            tenant_id="t1",
            execution_id="e2",
            title="Test 2",
            description="",
            priority=HITLPriority.MEDIUM,
        )
        
        stats = self.queue.get_queue_stats()
        assert stats["total_requests"] == 2
        assert stats["pending"] == 2
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["medium"] == 1


class TestHITLRequest:
    """Tests for HITLRequest model."""

    def test_time_in_queue(self):
        request = HITLRequest(
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Test",
            description="",
        )
        
        time_in_queue = request.time_in_queue()
        assert time_in_queue.total_seconds() >= 0

    def test_sla_not_breached(self):
        request = HITLRequest(
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Test",
            description="",
            sla_deadline=datetime.utcnow() + timedelta(hours=1),
        )
        
        assert request.is_sla_breached() is False

    def test_sla_breached(self):
        request = HITLRequest(
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Test",
            description="",
            sla_deadline=datetime.utcnow() - timedelta(hours=1),
        )
        
        assert request.is_sla_breached() is True

    def test_to_dict(self):
        request = HITLRequest(
            agent_id="a1",
            tenant_id="t1",
            execution_id="e1",
            title="Test",
            description="Test desc",
            priority=HITLPriority.HIGH,
        )
        
        data = request.to_dict()
        assert data["agent_id"] == "a1"
        assert data["title"] == "Test"
        assert data["priority"] == "high"
