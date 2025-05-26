import os
from typing import List, Optional

from fastembed import TextEmbedding as FastEmbedModelType
from pinecone import Index
from pinecone import Pinecone as PineconeClient
from pinecone import ServerlessSpec

from packages.shared.models import DocumentPayload

from .embeddings import get_fastembed_model

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "support-docs")
PINECONE_CLOUD_PROVIDER = os.getenv("PINECONE_CLOUD_PROVIDER", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-west-2")

_pinecone_client: Optional[PineconeClient] = None
_pinecone_index: Optional[Index] = None


def get_pinecone_client() -> PineconeClient:
    global _pinecone_client
    if _pinecone_client is None:
        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY not set in environment variables.")
        _pinecone_client = PineconeClient(api_key=PINECONE_API_KEY)
    return _pinecone_client


def get_pinecone_index(
    index_name: str = PINECONE_INDEX_NAME,
    dimension: Optional[int] = None,
    metric: str = "cosine",
    cloud: str = PINECONE_CLOUD_PROVIDER,
    region: str = PINECONE_REGION,
) -> Index:
    global _pinecone_index
    client = get_pinecone_client()
    if index_name not in client.list_indexes().names:
        print(f"Index '{index_name}' not found. Attempting to create...")
        if dimension is None:
            test_embed_model = get_fastembed_model()
            dimension = len(list(test_embed_model.embed(["test"]))[0])
            print(f"Determined embedding dimension: {dimension}")
        try:
            client.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud=cloud, region=region),
            )
            print(f"Index '{index_name}' created successfully.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"Index '{index_name}' already exists.")
            else:
                raise RuntimeError(
                    f"Failed to create Pinecone index '{index_name}': {e}"
                )
    _pinecone_index = client.Index(index_name)
    return _pinecone_index


async def upsert_documents_to_pinecone(
    documents: List[DocumentPayload],
    embedding_model: FastEmbedModelType,
    batch_size: int = 100,
) -> int:
    index = get_pinecone_index()
    vectors_to_upsert = []
    num_upserted = 0
    contents = [doc.content for doc in documents]
    embeddings_list = list(embedding_model.embed(contents))
    for i, doc in enumerate(documents):
        vectors_to_upsert.append(
            {
                "id": doc.id,
                "values": embeddings_list[i].tolist(),
                "metadata": {
                    "text": doc.content,
                    "source_url": str(doc.source_url),
                    "title": doc.title,
                    **doc.metadata,
                },
            }
        )
        if len(vectors_to_upsert) >= batch_size:
            index.upsert(vectors=vectors_to_upsert)
            num_upserted += len(vectors_to_upsert)
            vectors_to_upsert = []
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert)
        num_upserted += len(vectors_to_upsert)
    print(f"Upserted {num_upserted} documents to Pinecone index '{index.name}'.")
    return num_upserted


async def query_pinecone(
    query_text: str, embedding_model: FastEmbedModelType, top_k: int = 3
) -> List[dict]:
    index = get_pinecone_index()
    query_embedding = list(embedding_model.embed([query_text]))[0].tolist()
    query_response = index.query(
        vector=query_embedding, top_k=top_k, include_metadata=True
    )
    return query_response.get("matches", [])
