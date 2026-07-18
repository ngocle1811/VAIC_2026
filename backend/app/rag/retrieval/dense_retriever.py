"""Dense retrieval wrapper reusing Phase 2 embedding and vector-store boundaries."""

from app.rag.embeddings.service import EmbeddingService
from app.rag.index_models import VectorSearchFilters
from app.rag.retrieval.models import DenseSearchResult, RetrievalFilters
from app.rag.vectorstores.base import VectorStore


class DenseRetriever:
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def search(self, query: str, filters: RetrievalFilters, top_k: int) -> list[DenseSearchResult]:
        if not query.strip() or top_k < 1:
            raise ValueError("dense retrieval requires a query and positive top_k")
        vector = self.embedding_service.embed_query(query)
        store_filters = VectorSearchFilters(
            domain=filters.domain,
            document_types=filters.document_types,
            document_ids=filters.document_ids,
            document_status=filters.document_status,
            source=filters.source,
            document_number=filters.document_number,
            effective_on=filters.effective_on,
        )
        seen: set[str] = set()
        results = []
        for item in self.vector_store.search(vector, store_filters, top_k):
            if item.chunk_id in seen:
                continue
            seen.add(item.chunk_id)
            results.append(
                DenseSearchResult(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    document_name=item.document_name,
                    document_type=str(item.metadata.get("document_type", "")),
                    domain=str(item.metadata.get("domain", filters.domain or "")),
                    document_status=str(
                        item.metadata.get("document_status", filters.document_status)
                    ),
                    chunk_index=int(item.metadata.get("chunk_index", 0)),
                    content=item.content,
                    metadata=item.metadata,
                    retrieval_score=item.score,
                    dense_score=item.score,
                )
            )
        return results[:top_k]
