"""Opt-in Qdrant service lifecycle and persistence verification."""

from uuid import uuid4

import pytest
from qdrant_client import QdrantClient

from app.rag.index_models import EmbeddedChunk, VectorSearchFilters
from app.rag.models import (
    ChunkMetadata,
    DocumentChunk,
    DocumentDomain,
    DocumentStatus,
    DocumentType,
)
from app.rag.vectorstores.qdrant import QdrantVectorStore

pytestmark = pytest.mark.qdrant


def _chunk(document_id: str, chunk_id: str, vector: list[float]) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk=DocumentChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            document_name="SYNTHETIC_TEST_DATA",
            document_type=DocumentType.GUIDELINE,
            domain=DocumentDomain.TASKS,
            document_status=DocumentStatus.ACTIVE,
            chunk_index=0,
            content="SYNTHETIC_TEST_DATA deterministic retrieval content",
            metadata=ChunkMetadata(source_path="synthetic", parser_name="synthetic"),
        ),
        vector=vector,
        payload_metadata={"source": "SYNTHETIC_TEST_DATA"},
    )


def test_qdrant_create_upsert_filter_search_delete_and_persistence(
    integration_settings,
) -> None:
    if not integration_settings.run_local_integration_tests:
        pytest.skip("RUN_LOCAL_INTEGRATION_TESTS is not enabled")
    collection = f"ubnd_test_{uuid4().hex}"
    client = QdrantClient(url=integration_settings.qdrant_test_url)
    store = QdrantVectorStore(client, collection_name=collection)
    try:
        store.create_collection_if_missing(4)
        store.upsert_chunks(
            [
                _chunk("synthetic-doc", "chunk-1", [1.0, 0.0, 0.0, 0.0]),
                _chunk("other-doc", "chunk-2", [0.0, 1.0, 0.0, 0.0]),
            ]
        )
        results = store.search(
            [1.0, 0.0, 0.0, 0.0],
            VectorSearchFilters(document_id="synthetic-doc", domain="tasks"),
            5,
        )
        assert [item.chunk_id for item in results] == ["chunk-1"]

        second_client = QdrantClient(url=integration_settings.qdrant_test_url)
        persisted = QdrantVectorStore(second_client, collection_name=collection)
        assert persisted.count_by_document_id("synthetic-doc") == 1
        persisted.delete_by_document_id("synthetic-doc")
        assert persisted.count_by_document_id("synthetic-doc") == 0
        assert persisted.count_by_document_id("other-doc") == 1
    finally:
        client.delete_collection(collection)
