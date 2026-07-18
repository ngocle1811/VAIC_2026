"""Article-oriented chunking for Vietnamese legal documents."""

from collections.abc import Sequence

from app.rag.chunkers.base import BaseChunker
from app.rag.models import BlockType, DocumentBlock


class LegalDocumentChunker(BaseChunker):
    """Keep articles and their clauses/points together whenever size permits."""

    def partition(self, blocks: Sequence[DocumentBlock]) -> list[list[DocumentBlock]]:
        return self.pack(blocks, boundary_types=frozenset({BlockType.ARTICLE, BlockType.APPENDIX}))
