"""Embedding service construction from application settings."""

from app.config import Settings
from app.rag.embeddings.fpt import FPTEmbeddingProvider
from app.rag.embeddings.service import EmbeddingService


def create_embedding_service(settings: Settings) -> EmbeddingService:
    provider = FPTEmbeddingProvider(settings)
    return EmbeddingService(
        provider,
        batch_size=settings.embedding_batch_size,
        normalize=settings.embedding_normalize,
    )
