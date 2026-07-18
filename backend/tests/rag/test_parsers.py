from pathlib import Path

import pytest

from app.rag.exceptions import UnsupportedDocumentError
from app.rag.models import BlockType, DocumentDomain, DocumentType
from app.rag.parsers.docling import DoclingParser
from app.rag.parsers.docx import DOCXParser
from app.rag.parsers.factory import ParserFactory
from app.rag.parsers.pdf import PDFParser


def test_parser_factory_uses_specialized_fallbacks(monkeypatch) -> None:
    monkeypatch.setattr(DoclingParser, "is_available", classmethod(lambda cls: False))
    factory = ParserFactory()
    assert isinstance(factory.create("source.pdf"), PDFParser)
    assert isinstance(factory.create("source.docx"), DOCXParser)
    with pytest.raises(UnsupportedDocumentError):
        factory.create("source.txt")


def test_parser_factory_prefers_docling_when_available(monkeypatch) -> None:
    monkeypatch.setattr(DoclingParser, "is_available", classmethod(lambda cls: True))
    assert isinstance(ParserFactory().create("source.pdf"), DoclingParser)


def test_pdf_parser_preserves_pages(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "sample.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Dieu 1. Noi dung")
    pdf.new_page()
    pdf.save(path)
    pdf.close()

    parsed = PDFParser().parse(path, document_type=DocumentType.LEGAL, domain=DocumentDomain.COMMON)
    assert parsed.parser_name == "pymupdf"
    assert parsed.blocks[0].page_number == 1
    assert any(warning.code == "empty_page" for warning in parsed.warnings)


def test_docx_parser_preserves_headings_and_tables(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    path = tmp_path / "sample.docx"
    source = docx.Document()
    source.add_heading("THONG TIN CHUNG", level=1)
    source.add_paragraph("Noi dung")
    table = source.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Cot A"
    table.cell(0, 1).text = "Cot B"
    table.cell(1, 0).text = "1"
    table.cell(1, 1).text = "2"
    source.save(path)

    parsed = DOCXParser().parse(path, document_type=DocumentType.TEMPLATE)
    assert parsed.blocks[0].block_type == BlockType.HEADING
    assert parsed.blocks[-1].block_type == BlockType.TABLE
    assert parsed.blocks[-1].table is not None
    assert parsed.blocks[-1].table.headers == ["Cot A", "Cot B"]


def test_docx_parser_normalizes_heterogeneous_table_rows(tmp_path: Path) -> None:
    """Regression for Word tables whose logical rows expose different widths."""
    docx = pytest.importorskip("docx")
    path = tmp_path / "heterogeneous.docx"
    source = docx.Document()
    table = source.add_table(rows=2, cols=3)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "SYNTHETIC_TEST_DATA"
    table.cell(1, 0).text = "A"
    table.cell(1, 1).text = "B"
    table.cell(1, 2).text = "C"
    source.save(path)
    parsed = DOCXParser().parse(path, document_type=DocumentType.TEMPLATE)
    assert parsed.blocks[-1].table is not None
    assert len(parsed.blocks[-1].table.headers) == len(parsed.blocks[-1].table.rows[0])
