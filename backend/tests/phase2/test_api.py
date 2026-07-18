from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.routes.knowledge_base import get_knowledge_base_service
from app.main import app
from app.models.knowledge_document import ProcessingStatus
from app.schemas.knowledge_document import IngestionOutcome, IngestionResult


def _document(status: str = "ready") -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id="doc-1",
        original_filename="source.docx",
        document_name="Source",
        document_number=None,
        document_type="guideline",
        domain="common",
        document_status="active",
        processing_status=status,
        embedding_provider="fpt",
        embedding_model="Vietnamese_Embedding",
        embedding_dimension=4,
        chunk_count=1,
        uploaded_at=now,
        processing_started_at=now,
        processed_at=now,
        failed_stage=None,
        error_message=None,
    )


class StubService:
    def upload_and_ingest(self, request):
        assert request.source_path.exists()
        return IngestionResult(
            document_id="doc-1",
            processing_status=ProcessingStatus.READY,
            outcome=IngestionOutcome.INDEXED,
            chunk_count=1,
            embedding_model="Vietnamese_Embedding",
            embedding_dimension=4,
        )

    def list_documents(self, **filters):
        return [_document()]

    def get_document(self, document_id):
        return _document()

    def reindex_document(self, document_id):
        return IngestionResult(
            document_id=document_id,
            processing_status=ProcessingStatus.READY,
            outcome=IngestionOutcome.REINDEXED,
            chunk_count=1,
            embedding_model="Vietnamese_Embedding",
            embedding_dimension=4,
        )

    def delete_document(self, document_id):
        return _document("deleted")


def test_knowledge_base_api_crud() -> None:
    app.dependency_overrides[get_knowledge_base_service] = lambda: StubService()
    client = TestClient(app)
    try:
        upload = client.post(
            "/knowledge-base/documents",
            files={"file": ("source.docx", b"content", "application/octet-stream")},
            data={"domain": "common", "document_type": "guideline"},
        )
        assert upload.status_code == 201
        assert upload.json()["outcome"] == "indexed"
        assert client.get("/knowledge-base/documents").json()["items"][0]["id"] == "doc-1"
        assert client.get("/knowledge-base/documents/doc-1").status_code == 200
        assert (
            client.post("/knowledge-base/documents/doc-1/reindex").json()["outcome"] == "reindexed"
        )
        assert (
            client.delete("/knowledge-base/documents/doc-1").json()["processing_status"]
            == "deleted"
        )
    finally:
        app.dependency_overrides.clear()


def test_upload_validation_error() -> None:
    app.dependency_overrides[get_knowledge_base_service] = lambda: StubService()
    client = TestClient(app)
    try:
        response = client.post(
            "/knowledge-base/documents",
            files={"file": ("source.txt", b"content")},
            data={"domain": "invalid", "document_type": "guideline"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
