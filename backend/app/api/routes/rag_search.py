"""Thin Phase 3 endpoint returning retrieval evidence, never a generated answer."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.rag.retrieval.models import RAGSearchResult, RetrievalRequest
from app.services.rag import RAGService
from app.services.rag_factory import create_rag_service

router = APIRouter(prefix="/rag", tags=["rag"])


def get_rag_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RAGService:
    return create_rag_service(settings)


@router.post("/search", response_model=RAGSearchResult)
def search_rag(
    request: RetrievalRequest,
    service: Annotated[RAGService, Depends(get_rag_service)],
) -> RAGSearchResult:
    try:
        return service.search(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
