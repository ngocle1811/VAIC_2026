"""Searchable chunk corpus abstraction and deterministic in-memory implementation."""

from datetime import date
from typing import Protocol

from app.rag.retrieval.models import RetrievalFilters, SearchableChunk


class ChunkCorpusSource(Protocol):
    @property
    def version(self) -> str: ...

    def list_searchable_chunks(self, filters: RetrievalFilters) -> list[SearchableChunk]: ...

    def get_chunk(self, document_id: str, chunk_id: str) -> SearchableChunk | None: ...


class InMemoryChunkCorpusSource:
    def __init__(self, chunks: list[SearchableChunk] | None = None) -> None:
        self._chunks = list(chunks or [])
        self._version = 0

    @property
    def version(self) -> str:
        return str(self._version)

    def replace(self, chunks: list[SearchableChunk]) -> None:
        self._chunks = list(chunks)
        self._version += 1

    def list_searchable_chunks(self, filters: RetrievalFilters) -> list[SearchableChunk]:
        return [chunk for chunk in self._chunks if _matches(chunk, filters)]

    def get_chunk(self, document_id: str, chunk_id: str) -> SearchableChunk | None:
        return next(
            (
                chunk
                for chunk in self._chunks
                if chunk.document_id == document_id and chunk.chunk_id == chunk_id
            ),
            None,
        )


def _matches(chunk: SearchableChunk, filters: RetrievalFilters) -> bool:
    metadata = chunk.metadata
    if filters.domain and chunk.domain != filters.domain:
        return False
    if filters.document_types and chunk.document_type not in filters.document_types:
        return False
    if filters.document_ids and chunk.document_id not in filters.document_ids:
        return False
    if filters.document_status and chunk.document_status != filters.document_status:
        return False
    if filters.source and metadata.get("source") != filters.source:
        return False
    if filters.document_number and metadata.get("document_number") != filters.document_number:
        return False
    if metadata.get("processing_status") in filters.exclude_processing_statuses:
        return False
    if filters.effective_on:
        effective = _date(metadata.get("effective_date"))
        expiry = _date(metadata.get("expiry_date"))
        if effective and effective > filters.effective_on:
            return False
        if expiry and expiry < filters.effective_on:
            return False
    return True


def _date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None
