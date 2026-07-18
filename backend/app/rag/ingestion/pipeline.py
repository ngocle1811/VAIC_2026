"""Transactional-style orchestration for Phase 2 Knowledge Base ingestion."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from app.models.knowledge_document import KnowledgeDocument, ProcessingStatus
from app.rag.embeddings.input_builder import build_embedding_input
from app.rag.embeddings.service import EmbeddingService
from app.rag.exceptions import RAGError
from app.rag.index_models import EmbeddedChunk
from app.rag.pipeline import RAGPhase1Pipeline
from app.rag.vectorstores.base import VectorStore
from app.repositories.knowledge_document_repository import KnowledgeDocumentRepository
from app.schemas.knowledge_document import (
    IngestionOutcome,
    IngestionRequest,
    IngestionResult,
)
from app.services.knowledge_base_storage import KnowledgeBaseStorage

logger = logging.getLogger(__name__)


class IngestionError(RAGError):
    """Raised when a Phase 2 stage fails after safe lifecycle recording."""


class KnowledgeBaseIngestionPipeline:
    def __init__(
        self,
        *,
        repository: KnowledgeDocumentRepository,
        storage: KnowledgeBaseStorage,
        phase1_pipeline: RAGPhase1Pipeline,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        embedding_provider_name: str = "fpt",
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.phase1_pipeline = phase1_pipeline
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.embedding_provider_name = embedding_provider_name

    def ingest(self, request: IngestionRequest) -> IngestionResult:
        stage = "file_validation"
        document: KnowledgeDocument | None = None
        vector_write_started = False
        try:
            inspected = self.storage.inspect(request.source_path)
            existing = self.repository.get_by_checksum(inspected.checksum_sha256)
            if existing and not request.force_reindex:
                if (
                    existing.processing_status == ProcessingStatus.READY
                    and existing.embedding_model == self.embedding_service.model_name
                    and existing.embedding_dimension is not None
                ):
                    return self._result(existing, IngestionOutcome.SKIPPED_DUPLICATE)
                raise IngestionError(
                    "Document checksum already exists but is not compatible; "
                    "explicit reindex required"
                )

            if existing:
                document = existing
                managed_path = Path(existing.file_path)
                outcome = IngestionOutcome.REINDEXED
            else:
                stage = "file_storage"
                document_id = str(uuid4())
                stored = self.storage.store(request.source_path, document_id)
                document = self.repository.create_document(
                    id=document_id,
                    original_filename=stored.original_filename,
                    stored_filename=stored.stored_filename,
                    file_path=str(stored.file_path),
                    file_type=stored.file_type,
                    mime_type=stored.mime_type,
                    file_size_bytes=stored.file_size_bytes,
                    checksum_sha256=stored.checksum_sha256,
                    document_name=request.document_name,
                    document_number=request.document_number,
                    document_type=request.document_type.value,
                    domain=request.domain.value,
                    document_status=request.document_status.value,
                    processing_status=ProcessingStatus.UPLOADED,
                )
                managed_path = stored.file_path
                outcome = IngestionOutcome.INDEXED

            self.repository.mark_processing(document)
            stage = "phase1_processing"
            chunks = self.phase1_pipeline.process(
                managed_path,
                document_type=request.document_type,
                domain=request.domain,
                document_status=request.document_status,
                document_id=document.id,
            )
            stage = "chunk_validation"
            if not chunks:
                raise IngestionError("Phase 1 returned no chunks")
            for chunk in chunks:
                if chunk.document_id != document.id or not chunk.content.strip():
                    raise IngestionError("Phase 1 returned invalid chunk identity or content")

            stage = "embedding"
            inputs = [build_embedding_input(chunk) for chunk in chunks]
            vectors = self.embedding_service.embed_documents(inputs)
            if len(vectors) != len(chunks) or not vectors:
                raise IngestionError("Embedding count does not match chunk count")
            dimension = len(vectors[0])
            if not dimension or any(len(vector) != dimension for vector in vectors):
                raise IngestionError("Embedding dimensions are inconsistent")

            stage = "collection_validation"
            self.vector_store.create_collection_if_missing(dimension)
            if outcome == IngestionOutcome.REINDEXED:
                self.vector_store.delete_by_document_id(document.id)
            stage = "vector_upsert"
            vector_write_started = True
            semantic_metadata = self._semantic_metadata(request)
            self.vector_store.upsert_chunks(
                [
                    EmbeddedChunk(chunk=chunk, vector=vector, payload_metadata=semantic_metadata)
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ]
            )
            stage = "vector_verification"
            indexed_count = self.vector_store.count_by_document_id(document.id)
            if indexed_count != len(chunks):
                raise IngestionError(
                    f"Indexed chunk count mismatch: expected={len(chunks)}, actual={indexed_count}"
                )
            stage = "database_update"
            self.repository.mark_ready(
                document,
                provider=self.embedding_provider_name,
                model=self.embedding_service.model_name,
                dimension=dimension,
                chunk_count=len(chunks),
            )
            return self._result(document, outcome)
        except Exception as exc:
            if vector_write_started and document is not None:
                try:
                    self.vector_store.delete_by_document_id(document.id)
                except Exception:
                    logger.exception(
                        "Compensating vector cleanup failed",
                        extra={"document_id": document.id, "failed_stage": stage},
                    )
            if document is not None:
                self.repository.mark_failed(document, stage, self._safe_error(exc))
            logger.exception(
                "Knowledge Base ingestion failed",
                extra={
                    "document_id": document.id if document else None,
                    "failed_stage": stage,
                },
            )
            if isinstance(exc, IngestionError):
                raise
            raise IngestionError(f"Ingestion failed at {stage}: {self._safe_error(exc)}") from exc

    def reindex(self, document_id: str) -> IngestionResult:
        document = self.repository.get_by_id(document_id)
        if document is None or document.processing_status == ProcessingStatus.DELETED:
            raise IngestionError(f"Knowledge document not found: {document_id}")
        return self.ingest(
            IngestionRequest(
                source_path=Path(document.file_path),
                document_name=document.document_name,
                document_type=document.document_type,
                domain=document.domain,
                document_status=document.document_status,
                document_number=document.document_number,
                force_reindex=True,
            )
        )

    @staticmethod
    def _semantic_metadata(request: IngestionRequest) -> dict[str, object]:
        return {
            key: value
            for key, value in {
                "source": request.source,
                "document_number": request.document_number,
                "issued_date": request.issued_date.isoformat() if request.issued_date else None,
                "effective_date": (
                    request.effective_date.isoformat() if request.effective_date else None
                ),
            }.items()
            if value is not None
        }

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        return str(exc).replace("\n", " ")[:1000]

    @staticmethod
    def _result(document: KnowledgeDocument, outcome: IngestionOutcome) -> IngestionResult:
        return IngestionResult(
            document_id=document.id,
            processing_status=ProcessingStatus(document.processing_status),
            outcome=outcome,
            chunk_count=document.chunk_count,
            embedding_model=document.embedding_model,
            embedding_dimension=document.embedding_dimension,
        )
