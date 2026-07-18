"""Parser selection with optional Docling preference and explicit fallbacks."""

from pathlib import Path

from app.rag.exceptions import UnsupportedDocumentError
from app.rag.parsers.base import BaseParser
from app.rag.parsers.docling import DoclingParser
from app.rag.parsers.docx import DOCXParser
from app.rag.parsers.pdf import PDFParser


class ParserFactory:
    """Select the preferred available parser for a document extension."""

    def __init__(self, *, prefer_docling: bool = True) -> None:
        self.prefer_docling = prefer_docling

    def create(self, source_path: str | Path) -> BaseParser:
        suffix = Path(source_path).suffix.lower()
        if self.prefer_docling and DoclingParser.is_available() and suffix in {".pdf", ".docx"}:
            return DoclingParser()
        if suffix == ".pdf":
            return PDFParser()
        if suffix == ".docx":
            return DOCXParser()
        raise UnsupportedDocumentError(f"Unsupported document extension: {suffix or '<none>'}")
