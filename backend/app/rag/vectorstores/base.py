"""Provider-neutral dense vector store contract."""

from typing import Protocol

from app.rag.index_models import EmbeddedChunk, VectorSearchFilters, VectorSearchResult


class VectorStore(Protocol):
    def collection_exists(self) -> bool: ...

    def create_collection_if_missing(self, vector_size: int) -> None: ...

    def upsert_chunks(self, chunks: list[EmbeddedChunk]) -> None: ...

    def search(
        self,
        query_vector: list[float],
        filters: VectorSearchFilters | None,
        top_k: int,
    ) -> list[VectorSearchResult]: ...

    def delete_by_document_id(self, document_id: str) -> None: ...

    def count_by_document_id(self, document_id: str) -> int: ...
