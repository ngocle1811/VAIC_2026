"""Stable provider-neutral models for Phase 3 retrieval."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.rag.models import DocumentDomain, DocumentStatus, DocumentType


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    domain: DocumentDomain | None = None
    document_types: list[DocumentType] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    document_status: DocumentStatus | None = None
    source: str | None = None
    document_number: str | None = None
    effective_on: date | None = None
    retrieval_mode: Literal["auto", "dense", "lexical", "hybrid"] = "auto"
    candidate_top_k: int | None = Field(default=None, ge=1, le=1000)
    final_top_k: int | None = Field(default=None, ge=1, le=100)
    enable_hybrid: bool | None = None
    enable_reranker: bool | None = None
    expand_parent_context: bool | None = None
    debug: bool = False

    @model_validator(mode="after")
    def reject_blank_query(self) -> RetrievalRequest:
        if not self.query.strip():
            raise ValueError("retrieval query must not be blank")
        return self


class RetrievalFilters(BaseModel):
    domain: str | None = None
    document_types: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    document_status: str = "active"
    source: str | None = None
    document_number: str | None = None
    effective_on: date | None = None
    exclude_processing_statuses: list[str] = Field(default_factory=lambda: ["deleted"])


class RetrievalQueryPlan(BaseModel):
    original_query: str
    normalized_query: str
    exact_identifiers: list[str] = Field(default_factory=list)
    filters: RetrievalFilters
    candidate_top_k: int
    final_top_k: int
    use_dense: bool
    use_lexical: bool
    use_hybrid: bool
    use_reranker: bool
    expand_parent_context: bool


class SearchableChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    document_type: str
    domain: str
    document_status: str
    chunk_index: int = 0
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalCandidate(SearchableChunk):
    retrieval_score: float = 0.0
    dense_score: float | None = None
    lexical_score: float | None = None
    fused_score: float | None = None
    reranker_score: float | None = None


class DenseSearchResult(RetrievalCandidate):
    pass


class LexicalSearchResult(RetrievalCandidate):
    pass


class FusedSearchResult(RetrievalCandidate):
    pass


class RerankedChunk(RetrievalCandidate):
    pass


class ContextSource(BaseModel):
    source_id: str
    chunk_id: str
    document_id: str
    document_name: str
    document_number: str | None = None
    document_type: str
    domain: str
    source: str | None = None
    chapter: str | None = None
    section: str | None = None
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    heading: str | None = None
    page_number: int | None = None
    retrieval_score: float
    dense_score: float | None = None
    lexical_score: float | None = None
    fused_score: float | None = None
    reranker_score: float | None = None
    content: str


class BuiltContext(BaseModel):
    text: str
    sources: list[ContextSource]
    estimated_tokens: int = Field(ge=0)
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)


class CitationReference(BaseModel):
    source_id: str
    chunk_id: str | None = None
    document_id: str | None = None
    document_name: str | None = None


class RejectedCitation(BaseModel):
    citation: CitationReference
    reason: str


class CitationValidationResult(BaseModel):
    valid: bool
    accepted: list[CitationReference] = Field(default_factory=list)
    rejected: list[RejectedCitation] = Field(default_factory=list)


class RAGSearchResult(BaseModel):
    success: bool
    original_query: str
    normalized_query: str
    context: str
    sources: list[ContextSource]
    warnings: list[str] = Field(default_factory=list)
    retrieval_debug: dict[str, Any] | None = None
