import pytest

from app.rag.index_models import EmbeddedChunk, VectorSearchFilters
from app.rag.models import (
    ChunkMetadata,
    DocumentChunk,
    DocumentDomain,
    DocumentStatus,
    DocumentType,
)
from app.rag.vectorstores.qdrant import VectorStoreError
from app.services.vector_search import VectorSearchSmokeService


def _embedded(
    document_id: str,
    chunk_id: str,
    vector: list[float],
    *,
    domain: DocumentDomain = DocumentDomain.COMMON,
    document_type: DocumentType = DocumentType.LEGAL,
    payload_metadata: dict[str, object] | None = None,
) -> EmbeddedChunk:
    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name=f"{document_id}.pdf",
        document_type=document_type,
        domain=domain,
        document_status=DocumentStatus.ACTIVE,
        chunk_index=0,
        content=f"content {chunk_id}",
        metadata=ChunkMetadata(
            source_path="source.pdf", parser_name="test", page_numbers=[1], article="1"
        ),
    )
    return EmbeddedChunk(chunk=chunk, vector=vector, payload_metadata=payload_metadata or {})


def test_collection_creation_compatibility_and_stable_ids(vector_store) -> None:
    vector_store.create_collection_if_missing(4)
    vector_store.create_collection_if_missing(4)
    assert vector_store.collection_exists()
    with pytest.raises(VectorStoreError, match="dimension mismatch"):
        vector_store.create_collection_if_missing(3)
    assert vector_store.stable_point_id("d", "c") == vector_store.stable_point_id("d", "c")


def test_batch_upsert_count_filters_search_and_scoped_delete(vector_store) -> None:
    vector_store.create_collection_if_missing(4)
    vector_store.upsert_chunks(
        [
            _embedded("doc-a", "a1", [1, 0, 0, 0], domain=DocumentDomain.POPULATION),
            _embedded("doc-a", "a2", [0.9, 0.1, 0, 0], domain=DocumentDomain.POPULATION),
            _embedded(
                "doc-b",
                "b1",
                [0, 1, 0, 0],
                domain=DocumentDomain.TASKS,
                document_type=DocumentType.TEMPLATE,
            ),
        ]
    )
    assert vector_store.count_by_document_id("doc-a") == 2
    results = vector_store.search(
        [1, 0, 0, 0],
        VectorSearchFilters(domain="population", document_status="active"),
        5,
    )
    assert [result.document_id for result in results] == ["doc-a", "doc-a"]
    assert results[0].metadata["page_numbers"] == [1]
    assert not vector_store.search([1, 0, 0, 0], VectorSearchFilters(document_id="missing"), 5)
    vector_store.delete_by_document_id("doc-a")
    assert vector_store.count_by_document_id("doc-a") == 0
    assert vector_store.count_by_document_id("doc-b") == 1


def test_minimal_search_embeds_query_and_preserves_filters(
    vector_store, embedding_service, fake_provider
) -> None:
    vector_store.create_collection_if_missing(4)
    vector = embedding_service.embed_query("same query")
    vector_store.upsert_chunks([_embedded("doc-a", "a1", vector)])
    service = VectorSearchSmokeService(embedding_service, vector_store)
    results = service.search("same query", document_id="doc-a")
    assert fake_provider.query_calls == 2
    assert results[0].document_id == "doc-a"


def test_effective_date_filter_in_memory_qdrant(vector_store) -> None:
    from datetime import date

    vector_store.create_collection_if_missing(4)
    vector_store.upsert_chunks(
        [
            _embedded(
                "effective",
                "c1",
                [1, 0, 0, 0],
                payload_metadata={
                    "effective_date": "2099-01-01",
                    "expiry_date": "2099-12-31",
                },
            ),
            _embedded(
                "expired",
                "c2",
                [1, 0, 0, 0],
                payload_metadata={"expiry_date": "2098-12-31"},
            ),
        ]
    )
    results = vector_store.search(
        [1, 0, 0, 0], VectorSearchFilters(effective_on=date(2099, 6, 1)), 5
    )
    assert [item.document_id for item in results] == ["effective"]
