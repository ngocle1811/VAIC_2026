"""Optional Docling adapter for general high-fidelity document conversion."""

import importlib.util
import logging
from pathlib import Path

from app.rag.exceptions import DocumentParsingError, OptionalParserUnavailableError
from app.rag.models import (
    DocumentBlock,
    DocumentDomain,
    DocumentStatus,
    DocumentType,
    ParsedDocument,
    ParserWarning,
)
from app.rag.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class DoclingParser(BaseParser):
    """General parser loaded only when the optional Docling extra is installed."""

    supported_extensions = frozenset({".pdf", ".docx"})
    parser_name = "docling"

    @classmethod
    def is_available(cls) -> bool:
        return importlib.util.find_spec("docling") is not None

    def parse(
        self,
        source_path: str | Path,
        *,
        document_type: DocumentType,
        domain: DocumentDomain = DocumentDomain.COMMON,
        document_status: DocumentStatus = DocumentStatus.UNKNOWN,
        document_id: str | None = None,
    ) -> ParsedDocument:
        path = Path(source_path).resolve()
        if not path.is_file():
            raise DocumentParsingError(f"Document source does not exist: {path}")
        if not self.is_available():
            raise OptionalParserUnavailableError(
                "Docling is not installed; install the 'docling' optional dependency"
            )
        try:
            from docling.document_converter import DocumentConverter

            result = DocumentConverter().convert(path)
            markdown = result.document.export_to_markdown().strip()
        except Exception as exc:
            logger.exception(
                "Failed to parse document with Docling", extra={"source_path": str(path)}
            )
            raise DocumentParsingError(f"Docling failed for {path.name}: {exc}") from exc
        if not markdown:
            raise DocumentParsingError(f"Docling returned no content for {path.name}")
        block = DocumentBlock(block_id="b-000000", text=markdown, source_order=0)
        return ParsedDocument(
            document_id=document_id or self.source_id(path),
            document_name=path.name,
            source_path=path,
            mime_type=(
                "application/pdf"
                if path.suffix.lower() == ".pdf"
                else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            document_type=document_type,
            domain=domain,
            document_status=document_status,
            blocks=[block],
            warnings=[
                ParserWarning(
                    code="docling_markdown_projection",
                    message="Docling output was projected to a normalized Markdown block.",
                )
            ],
            parser_name=self.parser_name,
        )
