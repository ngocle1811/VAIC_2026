"""Select the strategy corresponding to validated document type."""

from app.rag.chunkers.base import BaseChunker
from app.rag.chunkers.guideline import GuidelineChunker
from app.rag.chunkers.legal import LegalDocumentChunker
from app.rag.chunkers.template import ReportTemplateChunker
from app.rag.config import DEFAULT_CHUNKING_CONFIG, ChunkingConfig
from app.rag.models import DocumentType


class ChunkerFactory:
    def __init__(self, config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG) -> None:
        self.config = config

    def create(self, document_type: DocumentType) -> BaseChunker:
        strategies: dict[DocumentType, type[BaseChunker]] = {
            DocumentType.LEGAL: LegalDocumentChunker,
            DocumentType.GUIDELINE: GuidelineChunker,
            DocumentType.TEMPLATE: ReportTemplateChunker,
        }
        return strategies[document_type](config=self.config)
