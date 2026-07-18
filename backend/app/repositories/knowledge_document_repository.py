"""Persistence-only operations for KnowledgeDocument lifecycle records."""

from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.knowledge_document import KnowledgeDocument, ProcessingStatus


class KnowledgeDocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_document(self, **values: object) -> KnowledgeDocument:
        document = KnowledgeDocument(**values)
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def get_by_id(self, document_id: str) -> KnowledgeDocument | None:
        return self.session.get(KnowledgeDocument, document_id)

    def get_by_checksum(self, checksum: str) -> KnowledgeDocument | None:
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.checksum_sha256 == checksum,
            KnowledgeDocument.processing_status != ProcessingStatus.DELETED,
        )
        return self.session.scalar(statement)

    def list_documents(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        domain: str | None = None,
        document_type: str | None = None,
        processing_status: str | None = None,
        document_status: str | None = None,
    ) -> list[KnowledgeDocument]:
        statement: Select[tuple[KnowledgeDocument]] = select(KnowledgeDocument)
        for column, value in (
            (KnowledgeDocument.domain, domain),
            (KnowledgeDocument.document_type, document_type),
            (KnowledgeDocument.processing_status, processing_status),
            (KnowledgeDocument.document_status, document_status),
        ):
            if value is not None:
                statement = statement.where(column == value)
        return list(self.session.scalars(statement.offset(offset).limit(limit)))

    def update_processing_status(
        self, document: KnowledgeDocument, status: ProcessingStatus
    ) -> None:
        document.processing_status = status
        self.session.commit()

    def mark_processing(self, document: KnowledgeDocument) -> None:
        document.processing_status = ProcessingStatus.PROCESSING
        document.processing_started_at = datetime.now(UTC)
        document.failed_stage = None
        document.error_message = None
        self.session.commit()

    def mark_ready(
        self,
        document: KnowledgeDocument,
        *,
        provider: str,
        model: str,
        dimension: int,
        chunk_count: int,
    ) -> None:
        document.processing_status = ProcessingStatus.READY
        document.embedding_provider = provider
        document.embedding_model = model
        document.embedding_dimension = dimension
        document.chunk_count = chunk_count
        document.processed_at = datetime.now(UTC)
        document.failed_stage = None
        document.error_message = None
        self.session.commit()

    def mark_failed(self, document: KnowledgeDocument, stage: str, message: str) -> None:
        document.processing_status = ProcessingStatus.FAILED
        document.failed_stage = stage
        document.error_message = message[:1000]
        self.session.commit()

    def mark_deleted(self, document: KnowledgeDocument) -> None:
        document.processing_status = ProcessingStatus.DELETED
        self.session.commit()
