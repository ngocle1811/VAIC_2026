"""Validated shared models passed through the Phase 1 RAG pipeline."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DocumentType(StrEnum):
    LEGAL = "legal"
    GUIDELINE = "guideline"
    TEMPLATE = "template"


class DocumentDomain(StrEnum):
    POPULATION = "population"
    COMPLAINTS = "complaints"
    TASKS = "tasks"
    COMMON = "common"


class DocumentStatus(StrEnum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    DRAFT = "draft"


class BlockType(StrEnum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    PART = "part"
    CHAPTER = "chapter"
    SECTION = "section"
    ARTICLE = "article"
    CLAUSE = "clause"
    POINT = "point"
    APPENDIX = "appendix"
    TEMPLATE_SECTION = "template_section"
    TABLE = "table"
    PAGE_BREAK = "page_break"


class ParserWarning(BaseModel):
    """Non-fatal parser diagnostic retained for observability."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    block_index: int | None = Field(default=None, ge=0)


class TableBlock(BaseModel):
    """Normalized tabular content with stable row and column ordering."""

    name: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_width(self) -> TableBlock:
        if self.headers and any(len(row) > len(self.headers) for row in self.rows):
            raise ValueError("table rows cannot be wider than headers")
        return self

    def as_text(self) -> str:
        lines = []
        if self.name:
            lines.append(self.name)
        if self.headers:
            lines.append(" | ".join(self.headers))
        lines.extend(" | ".join(row) for row in self.rows)
        return "\n".join(lines)


class DocumentBlock(BaseModel):
    """A source-preserving unit produced by parsing and enriched by analysis."""

    block_id: str = Field(min_length=1)
    block_type: BlockType = BlockType.PARAGRAPH
    text: str = ""
    page_number: int | None = Field(default=None, ge=1)
    heading_level: int | None = Field(default=None, ge=1, le=9)
    heading_hierarchy: list[str] = Field(default_factory=list)
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    parent_block_id: str | None = None
    table: TableBlock | None = None
    source_order: int = Field(ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_content(self) -> DocumentBlock:
        if self.block_type == BlockType.TABLE and self.table is None:
            raise ValueError("table blocks require table data")
        if not self.text.strip() and self.table is None and self.block_type != BlockType.PAGE_BREAK:
            raise ValueError("non-page-break blocks require text or table data")
        return self

    @property
    def content(self) -> str:
        return self.table.as_text() if self.table is not None else self.text


class ParsedDocument(BaseModel):
    """Parser-neutral representation of a PDF or DOCX source."""

    document_id: str = Field(min_length=1)
    document_name: str = Field(min_length=1)
    source_path: Path
    mime_type: str
    document_type: DocumentType
    domain: DocumentDomain = DocumentDomain.COMMON
    document_status: DocumentStatus = DocumentStatus.UNKNOWN
    blocks: list[DocumentBlock] = Field(default_factory=list)
    warnings: list[ParserWarning] = Field(default_factory=list)
    parser_name: str = Field(min_length=1)
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkMetadata(BaseModel):
    """Source and semantic context attached to an embedding-ready chunk."""

    model_config = ConfigDict(extra="forbid")

    source_path: str
    parser_name: str
    page_numbers: list[int] = Field(default_factory=list)
    heading_hierarchy: list[str] = Field(default_factory=list)
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    table_name: str | None = None
    parent_block_id: str | None = None
    parent_chunk_id: str | None = None
    block_ids: list[str] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    """Validated final unit ready for a future embedding step."""

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    document_name: str = Field(min_length=1)
    document_type: DocumentType
    domain: DocumentDomain
    document_status: DocumentStatus
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    metadata: ChunkMetadata


class StructureKind(StrEnum):
    PART = "part"
    CHAPTER = "chapter"
    SECTION = "section"
    ARTICLE = "article"
    CLAUSE = "clause"
    POINT = "point"
    HEADING = "heading"
    APPENDIX = "appendix"
    TEMPLATE_SECTION = "template_section"


class StructureMatch(BaseModel):
    kind: StructureKind
    label: str
    level: int = Field(ge=1)
    identifier: str | None = None
    title: str | None = None
    confidence: Literal["rule"] = "rule"
