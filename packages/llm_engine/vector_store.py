import logging
import os
from typing import Any

from fastembed import TextEmbedding as FastEmbedModelType
from pinecone import Pinecone as PineconeClient
from pinecone import ServerlessSpec

from packages.shared.models import DocumentPayload

from .embeddings import get_fastembed_model

logger = logging.getLogger(__name__)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "support-docs")
PINECONE_CLOUD_PROVIDER = os.getenv("PINECONE_CLOUD_PROVIDER", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-west-2")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "")
PINECONE_RERANK_MODEL = os.getenv("PINECONE_RERANK_MODEL", "bge-reranker-v2-m3")
PINECONE_RERANK_ENABLED = os.getenv("PINECONE_RERANK_ENABLED", "true").lower() == "true"

_pinecone_client: PineconeClient | None = None
_pinecone_index: Any | None = None  # Index type from client.Index()


def get_pinecone_client() -> PineconeClient:
    global _pinecone_client
    if _pinecone_client is None:
        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY not set in environment variables.")
        _pinecone_client = PineconeClient(api_key=PINECONE_API_KEY)
    return _pinecone_client


def get_pinecone_index(
    index_name: str = PINECONE_INDEX_NAME,
    dimension: int | None = None,
    metric: str = "cosine",
    cloud: str = PINECONE_CLOUD_PROVIDER,
    region: str = PINECONE_REGION,
) -> Any:
    global _pinecone_index
    client = get_pinecone_client()
    if index_name not in client.list_indexes().names:
        logger.info("Index '%s' not found. Attempting to create...", index_name)
        if dimension is None:
            test_embed_model = get_fastembed_model()
            dimension = len(list(test_embed_model.embed(["test"]))[0])
            logger.info("Determined embedding dimension: %d", dimension)
        try:
            client.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud=cloud, region=region),
            )
            logger.info("Index '%s' created successfully.", index_name)
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("Index '%s' already exists.", index_name)
            else:
                raise RuntimeError(f"Failed to create Pinecone index '{index_name}': {e}") from e
    _pinecone_index = client.Index(index_name)
    return _pinecone_index


async def upsert_documents_to_pinecone(
    documents: list[DocumentPayload],
    embedding_model: FastEmbedModelType,
    batch_size: int = 100,
    namespace: str = PINECONE_NAMESPACE,
) -> int:
    index = get_pinecone_index()
    vectors_to_upsert = []
    num_upserted = 0
    contents = [doc.content for doc in documents]
    embeddings_list = list(embedding_model.embed(contents))
    for i, doc in enumerate(documents):
        vectors_to_upsert.append({
            "id": doc.id,
            "values": embeddings_list[i].tolist(),
            "metadata": {
                "text": doc.content,
                "source_url": str(doc.source_url),
                "title": doc.title,
                **doc.metadata,
            },
        })
        if len(vectors_to_upsert) >= batch_size:
            index.upsert(vectors=vectors_to_upsert, namespace=namespace)
            num_upserted += len(vectors_to_upsert)
            vectors_to_upsert = []
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert, namespace=namespace)
        num_upserted += len(vectors_to_upsert)
    logger.info("Upserted %d documents to Pinecone index.", num_upserted)
    return num_upserted


async def query_pinecone(
    query_text: str,
    embedding_model: FastEmbedModelType,
    top_k: int = 3,
    namespace: str = PINECONE_NAMESPACE,
    metadata_filter: dict[str, Any] | None = None,
    rerank: bool = PINECONE_RERANK_ENABLED,
    rerank_top_n: int | None = None,
) -> list[dict]:
    """
    Query Pinecone with optional metadata filtering and integrated reranking.

    Args:
        query_text: The search query.
        embedding_model: FastEmbed model for generating query embeddings.
        top_k: Number of results to retrieve from the vector index.
        namespace: Pinecone namespace for tenant isolation.
        metadata_filter: Pinecone metadata filter dict (v2 syntax).
            Example: {"source_type": {"$eq": "faq"}, "updated_at": {"$gte": "2025-01-01"}}
        rerank: Whether to apply server-side reranking (requires Pinecone Serverless).
        rerank_top_n: Number of results after reranking (defaults to top_k).

    Returns:
        List of match dicts with score, id, and metadata.
    """
    index = get_pinecone_index()
    query_embedding = list(embedding_model.embed([query_text]))[0].tolist()

    query_kwargs: dict[str, Any] = {
        "vector": query_embedding,
        "top_k": top_k,
        "include_metadata": True,
        "namespace": namespace,
    }

    if metadata_filter:
        query_kwargs["filter"] = metadata_filter

    query_response = index.query(**query_kwargs)
    matches = query_response.get("matches", [])

    if rerank and matches and len(matches) > 1:
        matches = _rerank_results(query_text, matches, rerank_top_n or top_k)

    return matches


def _rerank_results(
    query: str,
    matches: list[dict],
    top_n: int,
) -> list[dict]:
    """
    Rerank results using Pinecone's integrated reranking API or a local fallback.

    Tries the Pinecone inference API first (Serverless v3), falls back to
    a simple keyword overlap heuristic if the API is unavailable.
    """
    try:
        client = get_pinecone_client()
        if hasattr(client, "inference") and hasattr(client.inference, "rerank"):
            documents = [
                {"id": m["id"], "text": m.get("metadata", {}).get("text", "")[:1000]}
                for m in matches
            ]
            reranked = client.inference.rerank(
                model=PINECONE_RERANK_MODEL,
                query=query,
                documents=[d["text"] for d in documents],
                top_n=top_n,
                return_documents=False,
            )
            id_to_match = {m["id"]: m for m in matches}
            reranked_matches = []
            for item in reranked.data:
                original_idx = item.index
                if original_idx < len(documents):
                    doc_id = documents[original_idx]["id"]
                    match = id_to_match.get(doc_id)
                    if match:
                        match = dict(match)
                        match["rerank_score"] = item.score
                        reranked_matches.append(match)
            logger.info(
                "Reranked %d -> %d results using %s",
                len(matches),
                len(reranked_matches),
                PINECONE_RERANK_MODEL,
            )
            return reranked_matches if reranked_matches else matches[:top_n]
    except Exception as e:
        logger.debug("Pinecone reranking unavailable, using fallback: %s", e)

    return _fallback_rerank(query, matches, top_n)


def _fallback_rerank(
    query: str,
    matches: list[dict],
    top_n: int,
) -> list[dict]:
    """
    Simple keyword-overlap reranking fallback when Pinecone reranking is unavailable.
    """
    query_terms = set(query.lower().split())

    def overlap_score(match: dict) -> float:
        text = match.get("metadata", {}).get("text", "").lower()
        text_terms = set(text.split())
        if not query_terms:
            return match.get("score", 0)
        overlap = len(query_terms & text_terms) / len(query_terms)
        return match.get("score", 0) * 0.7 + overlap * 0.3

    scored = sorted(matches, key=overlap_score, reverse=True)
    return scored[:top_n]


async def delete_by_metadata(
    metadata_filter: dict[str, Any],
    namespace: str = PINECONE_NAMESPACE,
) -> None:
    """
    Delete vectors matching a metadata filter.

    Useful for GDPR data deletion and document updates.

    Args:
        metadata_filter: Pinecone metadata filter dict.
        namespace: Pinecone namespace.
    """
    index = get_pinecone_index()
    index.delete(filter=metadata_filter, namespace=namespace)
    logger.info("Deleted vectors matching filter in namespace '%s'", namespace)


def get_index_stats() -> dict[str, Any]:
    """Get statistics about the Pinecone index."""
    try:
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        return {
            "total_vector_count": stats.get("total_vector_count", 0),
            "namespaces": stats.get("namespaces", {}),
            "dimension": stats.get("dimension", 0),
            "index_fullness": stats.get("index_fullness", 0),
        }
    except Exception as e:
        return {"error": str(e)[:200]}
