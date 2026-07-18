"""Validated construction of source metadata for final chunks."""

from collections.abc import Sequence

from app.rag.models import ChunkMetadata, DocumentBlock, ParsedDocument


class MetadataBuilder:
    """Build strict metadata without discarding available source context."""

    def build(
        self,
        document: ParsedDocument,
        blocks: Sequence[DocumentBlock],
        *,
        parent_chunk_id: str | None = None,
    ) -> ChunkMetadata:
        pages = sorted({block.page_number for block in blocks if block.page_number is not None})
        hierarchy = max((block.heading_hierarchy for block in blocks), key=len, default=[])
        return ChunkMetadata(
            source_path=str(document.source_path),
            parser_name=document.parser_name,
            page_numbers=pages,
            heading_hierarchy=hierarchy,
            article=self._last_value(blocks, "article"),
            clause=self._last_value(blocks, "clause"),
            point=self._last_value(blocks, "point"),
            table_name=next(
                (
                    block.table.name
                    for block in blocks
                    if block.table is not None and block.table.name
                ),
                None,
            ),
            parent_block_id=self._last_value(blocks, "parent_block_id"),
            parent_chunk_id=parent_chunk_id,
            block_ids=[block.block_id for block in blocks],
        )

    @staticmethod
    def _last_value(blocks: Sequence[DocumentBlock], attribute: str) -> str | None:
        return next(
            (
                value
                for block in reversed(blocks)
                if (value := getattr(block, attribute)) is not None
            ),
            None,
        )
