"""PyMuPDF parser used as the specialized PDF fallback."""

import logging
from pathlib import Path

from app.rag.exceptions import DocumentParsingError
from app.rag.models import (
    BlockType,
    DocumentBlock,
    DocumentDomain,
    DocumentStatus,
    DocumentType,
    ParsedDocument,
    ParserWarning,
)
from app.rag.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    supported_extensions = frozenset({".pdf"})
    parser_name = "pymupdf"

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
            raise DocumentParsingError(f"PDF source does not exist: {path}")
        try:
            import fitz
        except ImportError as exc:
            raise DocumentParsingError("PyMuPDF is required to parse PDF files") from exc

        blocks: list[DocumentBlock] = []
        warnings: list[ParserWarning] = []
        try:
            with fitz.open(path) as pdf:
                source_metadata = {key: value for key, value in pdf.metadata.items() if value}
                for page_index, page in enumerate(pdf):
                    page_number = page_index + 1
                    raw_blocks = page.get_text("blocks", sort=True)
                    page_has_text = False
                    for raw in raw_blocks:
                        text = str(raw[4]).strip()
                        if not text:
                            continue
                        page_has_text = True
                        order = len(blocks)
                        blocks.append(
                            DocumentBlock(
                                block_id=f"b-{order:06d}",
                                text=text,
                                page_number=page_number,
                                source_order=order,
                            )
                        )
                    if not page_has_text:
                        warnings.append(
                            ParserWarning(
                                code="empty_page",
                                message="No extractable text found; OCR is not enabled in Phase 1.",
                                page_number=page_number,
                            )
                        )
                    if page_index < pdf.page_count - 1:
                        order = len(blocks)
                        blocks.append(
                            DocumentBlock(
                                block_id=f"b-{order:06d}",
                                block_type=BlockType.PAGE_BREAK,
                                page_number=page_number,
                                source_order=order,
                            )
                        )
        except DocumentParsingError:
            raise
        except Exception as exc:
            logger.exception("Failed to parse PDF", extra={"source_path": str(path)})
            raise DocumentParsingError(f"Failed to parse PDF {path.name}: {exc}") from exc

        return ParsedDocument(
            document_id=document_id or self.source_id(path),
            document_name=path.name,
            source_path=path,
            mime_type="application/pdf",
            document_type=document_type,
            domain=domain,
            document_status=document_status,
            blocks=blocks,
            warnings=warnings,
            parser_name=self.parser_name,
            source_metadata=source_metadata,
        )
