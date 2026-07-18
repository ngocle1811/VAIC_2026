"""Batching and optional normalization above any embedding provider."""

import math

from app.rag.embeddings.base import EmbeddingProvider
from app.rag.embeddings.fpt import EmbeddingProviderError


class EmbeddingService:
    def __init__(
        self, provider: EmbeddingProvider, *, batch_size: int = 32, normalize: bool = True
    ) -> None:
        self.provider = provider
        self.batch_size = batch_size
        self.normalize = normalize

    @property
    def model_name(self) -> str:
        return self.provider.model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = self.provider.embed_documents(texts[start : start + self.batch_size])
            if len(batch) != len(texts[start : start + self.batch_size]):
                raise EmbeddingProviderError("Embedding provider returned an invalid vector count")
            vectors.extend(
                self._normalize(vector) if self.normalize else vector for vector in batch
            )
        self._validate_dimensions(vectors)
        return vectors

    def embed_query(self, query: str) -> list[float]:
        if not query.strip():
            raise EmbeddingProviderError("embedding query must not be empty")
        vector = self.provider.embed_query(query)
        return self._normalize(vector) if self.normalize else vector

    @staticmethod
    def _validate_dimensions(vectors: list[list[float]]) -> None:
        if not vectors:
            return
        dimension = len(vectors[0])
        if not dimension or any(len(vector) != dimension for vector in vectors):
            raise EmbeddingProviderError("Embedding vectors have inconsistent dimensions")

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            raise EmbeddingProviderError("Cannot normalize a zero embedding vector")
        return [value / norm for value in vector]
