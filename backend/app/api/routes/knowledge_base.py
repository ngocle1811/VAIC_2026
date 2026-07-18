"""Thin synchronous Knowledge Base management endpoints for Phase 2."""

import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_session
from app.models.knowledge_document import ProcessingStatus
from app.rag.ingestion.pipeline import IngestionError
from app.rag.models import DocumentDomain, DocumentStatus, DocumentType
from app.schemas.knowledge_document import (
    IngestionRequest,
    IngestionResult,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
)
from app.services.factory import create_knowledge_base_service
from app.services.knowledge_base import KnowledgeBaseService, KnowledgeDocumentNotFoundError

router = APIRouter(prefix="/knowledge-base/documents", tags=["knowledge-base"])


def get_knowledge_base_service(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> KnowledgeBaseService:
    return create_knowledge_base_service(session, settings)


@router.post("", response_model=IngestionResult, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: Annotated[UploadFile, File()],
    domain: Annotated[DocumentDomain, Form()],
    document_type: Annotated[DocumentType, Form()],
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)],
    document_name: Annotated[str | None, Form()] = None,
    document_status: Annotated[DocumentStatus, Form()] = DocumentStatus.ACTIVE,
    document_number: Annotated[str | None, Form()] = None,
) -> IngestionResult:
    suffix = Path(file.filename or "upload").suffix
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            shutil.copyfileobj(file.file, temporary)
            temporary_path = Path(temporary.name)
        return service.upload_and_ingest(
            IngestionRequest(
                source_path=temporary_path,
                document_name=document_name or file.filename or "document",
                document_type=document_type,
                domain=domain,
                document_status=document_status,
                document_number=document_number,
            )
        )
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@router.get("", response_model=KnowledgeDocumentListResponse)
def list_documents(
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    domain: DocumentDomain | None = None,
    document_type: DocumentType | None = None,
    processing_status: ProcessingStatus | None = None,
    document_status: DocumentStatus | None = None,
) -> KnowledgeDocumentListResponse:
    documents = service.list_documents(
        offset=offset,
        limit=limit,
        domain=domain.value if domain else None,
        document_type=document_type.value if document_type else None,
        processing_status=processing_status.value if processing_status else None,
        document_status=document_status.value if document_status else None,
    )
    return KnowledgeDocumentListResponse(
        items=[KnowledgeDocumentResponse.model_validate(document) for document in documents],
        offset=offset,
        limit=limit,
    )


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
def get_document(
    document_id: str,
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)],
) -> KnowledgeDocumentResponse:
    try:
        return KnowledgeDocumentResponse.model_validate(service.get_document(document_id))
    except KnowledgeDocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge document not found") from exc


@router.post("/{document_id}/reindex", response_model=IngestionResult)
def reindex_document(
    document_id: str,
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)],
) -> IngestionResult:
    try:
        return service.reindex_document(document_id)
    except KnowledgeDocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge document not found") from exc
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{document_id}", response_model=KnowledgeDocumentResponse)
def delete_document(
    document_id: str,
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)],
) -> KnowledgeDocumentResponse:
    try:
        return KnowledgeDocumentResponse.model_validate(service.delete_document(document_id))
    except KnowledgeDocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge document not found") from exc
