"""Minimal dense search used only to verify Phase 2 indexes."""

from app.rag.embeddings.service import EmbeddingService
from app.rag.index_models import VectorSearchFilters, VectorSearchResult
from app.rag.vectorstores.base import VectorStore


class VectorSearchSmokeService:
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        top_k: int = 5,
        domain: str | None = None,
        document_type: str | None = None,
        document_id: str | None = None,
        document_status: str | None = "active",
    ) -> list[VectorSearchResult]:
        vector = self.embedding_service.embed_query(query)
        filters = VectorSearchFilters(
            domain=domain,
            document_type=document_type,
            document_id=document_id,
            document_status=document_status,
        )
        return self.vector_store.search(vector, filters, top_k)
