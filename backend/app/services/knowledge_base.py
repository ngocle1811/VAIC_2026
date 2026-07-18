"""Business service between thin API routes and Phase 2 orchestration."""

from pathlib import Path

from app.models.knowledge_document import KnowledgeDocument
from app.rag.ingestion.pipeline import KnowledgeBaseIngestionPipeline
from app.rag.vectorstores.base import VectorStore
from app.repositories.knowledge_document_repository import KnowledgeDocumentRepository
from app.schemas.knowledge_document import IngestionRequest, IngestionResult


class KnowledgeDocumentNotFoundError(LookupError):
    pass


class KnowledgeBaseService:
    def __init__(
        self,
        repository: KnowledgeDocumentRepository,
        ingestion_pipeline: KnowledgeBaseIngestionPipeline,
        vector_store: VectorStore,
    ) -> None:
        self.repository = repository
        self.ingestion_pipeline = ingestion_pipeline
        self.vector_store = vector_store

    def upload_and_ingest(self, request: IngestionRequest) -> IngestionResult:
        return self.ingestion_pipeline.ingest(request)

    def get_document(self, document_id: str) -> KnowledgeDocument:
        document = self.repository.get_by_id(document_id)
        if document is None:
            raise KnowledgeDocumentNotFoundError(document_id)
        return document

    def list_documents(self, **filters: object) -> list[KnowledgeDocument]:
        return self.repository.list_documents(**filters)

    def reindex_document(self, document_id: str) -> IngestionResult:
        return self.ingestion_pipeline.reindex(document_id)

    def delete_document(self, document_id: str) -> KnowledgeDocument:
        document = self.get_document(document_id)
        self.vector_store.delete_by_document_id(document_id)
        self.repository.mark_deleted(document)
        return document


def ingestion_request_from_document(document: KnowledgeDocument) -> IngestionRequest:
    return IngestionRequest(
        source_path=Path(document.file_path),
        document_name=document.document_name,
        document_type=document.document_type,
        domain=document.domain,
        document_status=document.document_status,
        document_number=document.document_number,
        force_reindex=True,
    )
