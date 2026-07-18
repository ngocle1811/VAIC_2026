"""python-docx parser used as the specialized DOCX fallback."""

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
    TableBlock,
)
from app.rag.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class DOCXParser(BaseParser):
    supported_extensions = frozenset({".docx"})
    parser_name = "python-docx"

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
            raise DocumentParsingError(f"DOCX source does not exist: {path}")
        try:
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph
        except ImportError as exc:
            raise DocumentParsingError("python-docx is required to parse DOCX files") from exc

        blocks: list[DocumentBlock] = []
        try:
            document = Document(path)
            for item in document.iter_inner_content():
                order = len(blocks)
                if isinstance(item, Paragraph):
                    text = item.text.strip()
                    if not text:
                        continue
                    style_name = item.style.name if item.style else ""
                    is_heading = style_name.lower().startswith("heading")
                    level = None
                    if is_heading:
                        suffix = style_name.rsplit(" ", 1)[-1]
                        level = int(suffix) if suffix.isdigit() else 1
                    blocks.append(
                        DocumentBlock(
                            block_id=f"b-{order:06d}",
                            block_type=BlockType.HEADING if is_heading else BlockType.PARAGRAPH,
                            text=text,
                            heading_level=level,
                            source_order=order,
                            attributes={"style": style_name} if style_name else {},
                        )
                    )
                elif isinstance(item, Table):
                    matrix = [[cell.text.strip() for cell in row.cells] for row in item.rows]
                    if not matrix or not any(any(cell for cell in row) for row in matrix):
                        continue
                    width = max(len(row) for row in matrix)
                    normalized_matrix = [row + [""] * (width - len(row)) for row in matrix]
                    headers, rows = normalized_matrix[0], normalized_matrix[1:]
                    blocks.append(
                        DocumentBlock(
                            block_id=f"b-{order:06d}",
                            block_type=BlockType.TABLE,
                            source_order=order,
                            table=TableBlock(headers=headers, rows=rows),
                        )
                    )
            properties = document.core_properties
            source_metadata = {
                key: value
                for key, value in {
                    "title": properties.title,
                    "author": properties.author,
                    "subject": properties.subject,
                }.items()
                if value
            }
        except Exception as exc:
            logger.exception("Failed to parse DOCX", extra={"source_path": str(path)})
            raise DocumentParsingError(f"Failed to parse DOCX {path.name}: {exc}") from exc

        return ParsedDocument(
            document_id=document_id or self.source_id(path),
            document_name=path.name,
            source_path=path,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            document_type=document_type,
            domain=domain,
            document_status=document_status,
            blocks=blocks,
            parser_name=self.parser_name,
            source_metadata=source_metadata,
        )
