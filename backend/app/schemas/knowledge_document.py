"""Validated API and ingestion schemas for Knowledge Base documents."""

from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.models.knowledge_document import ProcessingStatus
from app.rag.models import DocumentDomain, DocumentStatus, DocumentType


class IngestionOutcome(StrEnum):
    INDEXED = "indexed"
    REINDEXED = "reindexed"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    FAILED = "failed"


class IngestionRequest(BaseModel):
    source_path: Path
    document_name: str = Field(min_length=1, max_length=512)
    document_type: DocumentType
    domain: DocumentDomain
    document_status: DocumentStatus = DocumentStatus.ACTIVE
    document_number: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=512)
    issued_date: date | None = None
    effective_date: date | None = None
    force_reindex: bool = False


class IngestionResult(BaseModel):
    document_id: str
    processing_status: ProcessingStatus
    outcome: IngestionOutcome
    chunk_count: int = Field(ge=0)
    embedding_model: str | None = None
    embedding_dimension: int | None = Field(default=None, ge=1)
    warnings: list[str] = Field(default_factory=list)


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    document_name: str
    document_number: str | None
    document_type: str
    domain: str
    document_status: str
    processing_status: str
    embedding_provider: str | None
    embedding_model: str | None
    embedding_dimension: int | None
    chunk_count: int
    uploaded_at: datetime
    processing_started_at: datetime | None
    processed_at: datetime | None
    failed_stage: str | None
    error_message: str | None


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentResponse]
    offset: int
    limit: int
