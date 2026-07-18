"""Safe dense-vector Qdrant adapter for Phase 2 indexing and smoke search."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from app.rag.exceptions import RAGError
from app.rag.index_models import EmbeddedChunk, VectorSearchFilters, VectorSearchResult
from app.rag.retrieval.models import RetrievalFilters, SearchableChunk


class VectorStoreError(RAGError):
    """Raised when collection safety or vector persistence checks fail."""


class QdrantVectorStore:
    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        distance: str = "COSINE",
        upsert_batch_size: int = 64,
    ) -> None:
        self.client = client
        self.collection_name = collection_name
        self.distance = models.Distance[distance.upper()]
        self.upsert_batch_size = upsert_batch_size
        self._mutation_revision = 0

    def collection_exists(self) -> bool:
        return self.client.collection_exists(self.collection_name)

    @property
    def version(self) -> str:
        if not self.collection_exists():
            return "missing"
        info = self.client.get_collection(self.collection_name)
        return f"{info.points_count}:{info.indexed_vectors_count}:{self._mutation_revision}"

    def create_collection_if_missing(self, vector_size: int) -> None:
        if not self.collection_exists():
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=self.distance),
            )
            return
        info = self.client.get_collection(self.collection_name)
        vectors = info.config.params.vectors
        if not isinstance(vectors, models.VectorParams):
            raise VectorStoreError("Named or sparse vector collections are unsupported in Phase 2")
        if vectors.size != vector_size:
            raise VectorStoreError(
                f"Qdrant dimension mismatch: collection={vectors.size}, embedding={vector_size}"
            )
        if vectors.distance != self.distance:
            raise VectorStoreError(
                f"Qdrant distance mismatch: collection={vectors.distance}, "
                f"configured={self.distance}"
            )

    def upsert_chunks(self, chunks: list[EmbeddedChunk]) -> None:
        for start in range(0, len(chunks), self.upsert_batch_size):
            points = [self._point(item) for item in chunks[start : start + self.upsert_batch_size]]
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
            self._mutation_revision += 1

    def search(
        self,
        query_vector: list[float],
        filters: VectorSearchFilters | None = None,
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=self._filter(filters),
            limit=top_k,
            with_payload=True,
        )
        return [self._result(point) for point in result.points]

    def delete_by_document_id(self, document_id: str) -> None:
        if not self.collection_exists():
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id", match=models.MatchValue(value=document_id)
                        )
                    ]
                )
            ),
            wait=True,
        )
        self._mutation_revision += 1

    def count_by_document_id(self, document_id: str) -> int:
        if not self.collection_exists():
            return 0
        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id", match=models.MatchValue(value=document_id)
                    )
                ]
            ),
            exact=True,
        )
        return result.count

    def list_searchable_chunks(self, filters: RetrievalFilters) -> list[SearchableChunk]:
        if not self.collection_exists():
            return []
        vector_filters = VectorSearchFilters(
            domain=filters.domain,
            document_types=filters.document_types,
            document_ids=filters.document_ids,
            document_status=filters.document_status,
            source=filters.source,
            document_number=filters.document_number,
            effective_on=filters.effective_on,
        )
        chunks: list[SearchableChunk] = []
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=self._filter(vector_filters),
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            chunks.extend(self._searchable(point.payload or {}) for point in points)
            if offset is None:
                return chunks

    def get_chunk(self, document_id: str, chunk_id: str) -> SearchableChunk | None:
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id", match=models.MatchValue(value=document_id)
                    ),
                    models.FieldCondition(key="chunk_id", match=models.MatchValue(value=chunk_id)),
                ]
            ),
            limit=1,
            with_payload=True,
            with_vectors=False,
        )
        return self._searchable(points[0].payload or {}) if points else None

    @staticmethod
    def stable_point_id(document_id: str, chunk_id: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"ubnd-kb:{document_id}:{chunk_id}"))

    def _point(self, embedded: EmbeddedChunk) -> models.PointStruct:
        chunk = embedded.chunk
        payload = {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "document_name": chunk.document_name,
            "document_type": chunk.document_type.value,
            "domain": chunk.domain.value,
            "document_status": chunk.document_status.value,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "metadata": chunk.metadata.model_dump(mode="json"),
        }
        payload["metadata"].update(embedded.payload_metadata)
        return models.PointStruct(
            id=self.stable_point_id(chunk.document_id, chunk.chunk_id),
            vector=embedded.vector,
            payload=payload,
        )

    @staticmethod
    def _filter(filters: VectorSearchFilters | None) -> models.Filter | None:
        if filters is None:
            return None
        conditions = []
        for key, value in (
            ("domain", filters.domain),
            ("document_type", filters.document_type),
            ("document_id", filters.document_id),
            ("document_status", filters.document_status),
            ("metadata.source", filters.source),
            ("metadata.document_number", filters.document_number),
        ):
            if value is not None:
                conditions.append(
                    models.FieldCondition(key=key, match=models.MatchValue(value=value))
                )
        if filters.document_types:
            conditions.append(
                models.FieldCondition(
                    key="document_type", match=models.MatchAny(any=filters.document_types)
                )
            )
        if filters.document_ids:
            conditions.append(
                models.FieldCondition(
                    key="document_id", match=models.MatchAny(any=filters.document_ids)
                )
            )
        if filters.effective_on:
            conditions.extend(
                [
                    models.Filter(
                        should=[
                            models.FieldCondition(
                                key="metadata.effective_date",
                                range=models.DatetimeRange(lte=filters.effective_on),
                            ),
                            models.IsEmptyCondition(
                                is_empty=models.PayloadField(key="metadata.effective_date")
                            ),
                        ]
                    ),
                    models.Filter(
                        should=[
                            models.FieldCondition(
                                key="metadata.expiry_date",
                                range=models.DatetimeRange(gte=filters.effective_on),
                            ),
                            models.IsEmptyCondition(
                                is_empty=models.PayloadField(key="metadata.expiry_date")
                            ),
                        ]
                    ),
                ]
            )
        return models.Filter(must=conditions) if conditions else None

    @staticmethod
    def _result(point: models.ScoredPoint) -> VectorSearchResult:
        payload = point.payload or {}
        metadata = dict(payload.get("metadata", {}))
        for key in ("document_type", "domain", "document_status", "chunk_index"):
            metadata[key] = payload.get(key)
        return VectorSearchResult(
            chunk_id=str(payload.get("chunk_id", "")),
            document_id=str(payload.get("document_id", "")),
            document_name=str(payload.get("document_name", "")),
            content=str(payload.get("content", "")),
            score=point.score,
            metadata=metadata,
        )

    @staticmethod
    def _searchable(payload: dict[str, object]) -> SearchableChunk:
        return SearchableChunk(
            chunk_id=str(payload.get("chunk_id", "")),
            document_id=str(payload.get("document_id", "")),
            document_name=str(payload.get("document_name", "")),
            document_type=str(payload.get("document_type", "")),
            domain=str(payload.get("domain", "")),
            document_status=str(payload.get("document_status", "")),
            chunk_index=int(payload.get("chunk_index", 0)),
            content=str(payload.get("content", "")),
            metadata=dict(payload.get("metadata", {})),
        )
