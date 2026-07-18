"""Shared size handling and final model construction for chunking strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.rag.config import DEFAULT_CHUNKING_CONFIG, ChunkingConfig
from app.rag.exceptions import ChunkingError
from app.rag.metadata import MetadataBuilder
from app.rag.models import BlockType, DocumentBlock, DocumentChunk, ParsedDocument


class BaseChunker(ABC):
    """Base for document-type-specific, structure-aware chunkers."""

    def __init__(
        self,
        config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
        metadata_builder: MetadataBuilder | None = None,
    ) -> None:
        self.config = config
        self.metadata_builder = metadata_builder or MetadataBuilder()

    def chunk(self, document: ParsedDocument) -> list[DocumentChunk]:
        content_blocks = [
            block for block in document.blocks if block.block_type != BlockType.PAGE_BREAK
        ]
        if not content_blocks:
            raise ChunkingError(f"Document {document.document_name} has no content to chunk")
        groups = self.partition(content_blocks)
        chunks: list[DocumentChunk] = []
        for group in groups:
            content = self.render(group)
            if not content:
                continue
            for segment_index, segment in enumerate(self._split_text(content)):
                chunk_index = len(chunks)
                chunk_id = f"{document.document_id}-chunk-{chunk_index:05d}"
                parent_chunk_id = None
                if segment_index > 0:
                    parent_chunk_id = (
                        f"{document.document_id}-chunk-{chunk_index - segment_index:05d}"
                    )
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document.document_id,
                        document_name=document.document_name,
                        document_type=document.document_type,
                        domain=document.domain,
                        document_status=document.document_status,
                        chunk_index=chunk_index,
                        content=segment,
                        metadata=self.metadata_builder.build(
                            document, group, parent_chunk_id=parent_chunk_id
                        ),
                    )
                )
        return chunks

    @abstractmethod
    def partition(self, blocks: Sequence[DocumentBlock]) -> list[list[DocumentBlock]]:
        """Group blocks along semantic boundaries before size splitting."""

    def pack(
        self,
        blocks: Sequence[DocumentBlock],
        *,
        boundary_types: frozenset[BlockType],
        isolate_tables: bool = False,
    ) -> list[list[DocumentBlock]]:
        groups: list[list[DocumentBlock]] = []
        current: list[DocumentBlock] = []
        current_size = 0
        for block in blocks:
            size = len(block.content)
            starts_boundary = block.block_type in boundary_types and bool(current)
            exceeds_target = current_size + size > self.config.target_size and bool(current)
            if (
                starts_boundary
                or exceeds_target
                or (isolate_tables and block.table is not None and current)
            ):
                groups.append(current)
                current, current_size = [], 0
            current.append(block)
            current_size += size + 2
            if isolate_tables and block.table is not None:
                groups.append(current)
                current, current_size = [], 0
        if current:
            groups.append(current)
        return groups

    @staticmethod
    def render(blocks: Sequence[DocumentBlock]) -> str:
        return "\n\n".join(block.content.strip() for block in blocks if block.content.strip())

    def _split_text(self, text: str) -> list[str]:
        if len(text) <= self.config.max_size:
            return [text]
        segments: list[str] = []
        start = 0
        while start < len(text):
            limit = min(start + self.config.max_size, len(text))
            end = limit
            if limit < len(text):
                candidates = [text.rfind(marker, start, limit) for marker in ("\n\n", ". ", "; ")]
                boundary = max(candidates)
                if boundary > start + self.config.target_size // 2:
                    end = boundary + 1
            segment = text[start:end].strip()
            if segment:
                segments.append(segment)
            if end >= len(text):
                break
            start = max(end - self.config.overlap, start + 1)
        return segments
