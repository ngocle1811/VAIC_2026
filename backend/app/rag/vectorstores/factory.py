"""Qdrant adapter construction isolated from business services."""

from qdrant_client import QdrantClient

from app.config import Settings
from app.rag.vectorstores.qdrant import QdrantVectorStore


def create_vector_store(settings: Settings) -> QdrantVectorStore:
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    return QdrantVectorStore(
        client,
        collection_name=settings.qdrant_collection,
        distance=settings.qdrant_distance,
        upsert_batch_size=settings.qdrant_upsert_batch_size,
    )
