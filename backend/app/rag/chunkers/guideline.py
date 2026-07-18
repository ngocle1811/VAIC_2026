"""Heading-oriented chunking for reporting guidelines and procedures."""

from collections.abc import Sequence

from app.rag.chunkers.base import BaseChunker
from app.rag.models import BlockType, DocumentBlock


class GuidelineChunker(BaseChunker):
    """Start chunks at procedural headings and major administrative sections."""

    def partition(self, blocks: Sequence[DocumentBlock]) -> list[list[DocumentBlock]]:
        return self.pack(
            blocks,
            boundary_types=frozenset(
                {
                    BlockType.PART,
                    BlockType.CHAPTER,
                    BlockType.SECTION,
                    BlockType.HEADING,
                    BlockType.APPENDIX,
                }
            ),
        )
