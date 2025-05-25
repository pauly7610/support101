import pytest
from unittest.mock import AsyncMock, patch
from packages.llm_engine.chains.rag_chain import RAGChain, SIMILARITY_THRESHOLD
from packages.shared.models import TicketContext

@pytest.mark.asyncio
async def test_rag_chain_mock_llm(monkeypatch):
    rag = RAGChain()
    # Mock the chain's LLM output
    rag.chain.ainvoke = AsyncMock(return_value="Mocked LLM response.")
    ticket = TicketContext(user_query="What is SOC2?")
    resp = await rag.invoke(ticket)
    assert resp.reply_text == "Mocked LLM response."

@pytest.mark.asyncio
async def test_rag_chain_similarity_threshold(monkeypatch):
    rag = RAGChain()
    # Patch _safe_query_pinecone to return below/above threshold
    async def mock_query(question, top_k=3):
        return [
            {"metadata": {"text": "Relevant", "source_url": "url", "title": "t"}, "score": SIMILARITY_THRESHOLD + 0.01},
            {"metadata": {"text": "Irrelevant", "source_url": "url", "title": "t"}, "score": SIMILARITY_THRESHOLD - 0.01}
        ]
    monkeypatch.setattr(rag, "_safe_query_pinecone", mock_query)
    context = await rag._retrieve_and_format_context({"question": "test"})
    assert "Relevant" in context
    assert "Irrelevant" not in context

@pytest.mark.asyncio
async def test_rag_chain_timeout(monkeypatch):
    rag = RAGChain()
    async def slow_chain(*args, **kwargs):
        import asyncio
        await asyncio.sleep(31)
    rag.chain.ainvoke = slow_chain
    ticket = TicketContext(user_query="Timeout?")
    resp = await rag.invoke(ticket)
    assert resp.error["error_type"] == "llm_timeout"
