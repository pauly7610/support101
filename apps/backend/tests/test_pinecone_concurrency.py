import pytest
import threading
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_pinecone_index():
    mock_index = MagicMock()
    # Simulate upsert latency and thread-safety
    def upsert(vectors, *args, **kwargs):
        # Optionally, add a small sleep to simulate network delay
        return {"upserted_count": len(vectors)}
    mock_index.upsert.side_effect = upsert
    return mock_index


def test_pinecone_concurrent_upserts(mock_pinecone_index):
    """Test concurrent upserts to Pinecone vector store (mocked) for thread safety."""
    results = []
    errors = []
    def upsert_job():
        try:
            resp = mock_pinecone_index.upsert([[1]*768], namespace="test")
            results.append(resp["upserted_count"])
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=upsert_job) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(count == 1 for count in results), f"Unexpected upsert counts: {results}"
    assert not errors, f"Errors occurred during concurrent upserts: {errors}"
