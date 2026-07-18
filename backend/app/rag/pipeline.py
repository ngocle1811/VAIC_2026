"""Composable orchestration for the complete Phase 1 data flow."""

from pathlib import Path

from app.rag.chunkers.factory import ChunkerFactory
from app.rag.models import (
    DocumentChunk,
    DocumentDomain,
    DocumentStatus,
    DocumentType,
)
from app.rag.parsers.factory import ParserFactory
from app.rag.processing.cleaner import TextCleaner
from app.rag.processing.structure import VietnameseStructureAnalyzer


class RAGPhase1Pipeline:
    """Parse, clean, analyze, chunk, and validate a PDF or DOCX."""

    def __init__(
        self,
        parser_factory: ParserFactory | None = None,
        cleaner: TextCleaner | None = None,
        analyzer: VietnameseStructureAnalyzer | None = None,
        chunker_factory: ChunkerFactory | None = None,
    ) -> None:
        self.parser_factory = parser_factory or ParserFactory()
        self.cleaner = cleaner or TextCleaner()
        self.analyzer = analyzer or VietnameseStructureAnalyzer()
        self.chunker_factory = chunker_factory or ChunkerFactory()

    def process(
        self,
        source_path: str | Path,
        *,
        document_type: DocumentType,
        domain: DocumentDomain = DocumentDomain.COMMON,
        document_status: DocumentStatus = DocumentStatus.UNKNOWN,
        document_id: str | None = None,
    ) -> list[DocumentChunk]:
        parser = self.parser_factory.create(source_path)
        parsed = parser.parse(
            source_path,
            document_type=document_type,
            domain=domain,
            document_status=document_status,
            document_id=document_id,
        )
        cleaned = self.cleaner.clean(parsed)
        analyzed = self.analyzer.analyze(cleaned)
        chunker = self.chunker_factory.create(document_type)
        return chunker.chunk(analyzed)
