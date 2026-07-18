"""Field- and table-preserving chunking for report templates."""

from collections.abc import Sequence

from app.rag.chunkers.base import BaseChunker
from app.rag.models import BlockType, DocumentBlock


class ReportTemplateChunker(BaseChunker):
    """Keep template sections distinct and tables intact as source units."""

    def partition(self, blocks: Sequence[DocumentBlock]) -> list[list[DocumentBlock]]:
        return self.pack(
            blocks,
            boundary_types=frozenset(
                {BlockType.TEMPLATE_SECTION, BlockType.HEADING, BlockType.APPENDIX}
            ),
            isolate_tables=True,
        )
