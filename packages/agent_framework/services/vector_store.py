"""
Pinecone vector store service for agent framework.

Wraps Pinecone client for knowledge base search, similarity queries,
and document management. Users must set PINECONE_API_KEY in their
environment to enable real vector store calls.
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PINECONE_AVAILABLE = False

try:
    from pinecone import Pinecone as PineconeClient

    _PINECONE_AVAILABLE = True
except ImportError:
    logger.debug("pinecone not installed; VectorStoreService will use stubs")

_FASTEMBED_AVAILABLE = False

try:
    from fastembed import TextEmbedding

    _FASTEMBED_AVAILABLE = True
except ImportError:
    logger.debug("fastembed not installed; VectorStoreService will use stubs")


class VectorStoreService:
    """
    Pinecone vector store service for agent operations.

    Requires env vars:
        PINECONE_API_KEY — Pinecone API key
        PINECONE_INDEX_NAME — Index name (default: support-docs)

    Falls back to empty results when Pinecone is not configured.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        embedding_model_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        self._api_key = api_key or os.getenv("PINECONE_API_KEY")
        self._index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "support-docs")
        self._embedding_model_name = embedding_model_name
        self._client: Optional[Any] = None
        self._index: Optional[Any] = None
        self._embed_model: Optional[Any] = None

    @property
    def available(self) -> bool:
        return bool(self._api_key) and _PINECONE_AVAILABLE

    def _ensure_client(self) -> bool:
        if self._client is not None:
            return True
        if not self.available:
            return False
        try:
            self._client = PineconeClient(api_key=self._api_key)
            self._index = self._client.Index(self._index_name)
            logger.info("VectorStoreService: connected to index '%s'", self._index_name)
            return True
        except Exception as e:
            logger.warning("VectorStoreService: failed to connect: %s", e)
            return False

    def _ensure_embed_model(self) -> bool:
        if self._embed_model is not None:
            return True
        if not _FASTEMBED_AVAILABLE:
            return False
        try:
            self._embed_model = TextEmbedding(
                model_name=self._embedding_model_name, max_length=512
            )
            return True
        except Exception as e:
            logger.warning("VectorStoreService: failed to load embedding model: %s", e)
            return False

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if not self._ensure_embed_model():
            return []
        return [emb.tolist() for emb in self._embed_model.embed(texts)]

    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search the vector store for relevant documents.

        Returns list of matches with content, source, and score.
        Falls back to empty list when unavailable.
        """
        if not self._ensure_client():
            return []

        embeddings = self._embed([query])
        if not embeddings:
            return []

        try:
            kwargs: Dict[str, Any] = {
                "vector": embeddings[0],
                "top_k": top_k,
                "include_metadata": True,
            }
            if filter_metadata:
                kwargs["filter"] = filter_metadata

            response = self._index.query(**kwargs)
            matches = response.get("matches", [])

            results = []
            for match in matches:
                score = match.get("score", 0.0)
                if score < min_score:
                    continue
                meta = match.get("metadata", {})
                results.append({
                    "id": match.get("id", ""),
                    "content": meta.get("text", ""),
                    "source": meta.get("source_url", ""),
                    "title": meta.get("title", ""),
                    "score": score,
                })
            return results
        except Exception as e:
            logger.warning("VectorStoreService: search failed: %s", e)
            return []

    async def upsert(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """
        Upsert documents into the vector store.

        Each document should have: id, content, metadata (dict).
        Returns number of documents upserted.
        """
        if not self._ensure_client():
            return 0

        contents = [d.get("content", "") for d in documents]
        embeddings = self._embed(contents)
        if not embeddings or len(embeddings) != len(documents):
            return 0

        vectors = []
        for i, doc in enumerate(documents):
            meta = doc.get("metadata", {})
            meta["text"] = doc.get("content", "")[:5000]
            vectors.append({
                "id": doc["id"],
                "values": embeddings[i],
                "metadata": meta,
            })

        upserted = 0
        try:
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i : i + batch_size]
                self._index.upsert(vectors=batch)
                upserted += len(batch)
        except Exception as e:
            logger.warning("VectorStoreService: upsert failed after %d docs: %s", upserted, e)

        return upserted

    async def delete(self, ids: List[str]) -> bool:
        """Delete documents by ID."""
        if not self._ensure_client():
            return False
        try:
            self._index.delete(ids=ids)
            return True
        except Exception as e:
            logger.warning("VectorStoreService: delete failed: %s", e)
            return False


_vs_service: Optional[VectorStoreService] = None


def get_vector_store_service() -> VectorStoreService:
    global _vs_service
    if _vs_service is None:
        _vs_service = VectorStoreService()
    return _vs_service
