from pathlib import Path

from app.rag.models import DocumentBlock, DocumentType, ParsedDocument
from app.rag.processing.cleaner import TextCleaner


def _document(tmp_path: Path, blocks: list[DocumentBlock]) -> ParsedDocument:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"x")
    return ParsedDocument(
        document_id="d1",
        document_name="source.pdf",
        source_path=source,
        mime_type="application/pdf",
        document_type=DocumentType.LEGAL,
        parser_name="test",
        blocks=blocks,
    )


def test_unicode_and_broken_lines_are_cleaned_conservatively() -> None:
    cleaner = TextCleaner()
    assert cleaner.clean_text("Công văn\nliên quan") == "Công văn liên quan"
    assert cleaner.clean_text("Điều 1. Phạm vi\n1. Nội dung") == "Điều 1. Phạm vi\n1. Nội dung"
    assert cleaner.clean_text("Số: 12/QĐ-UBND\nNgày ban hành") == "Số: 12/QĐ-UBND\nNgày ban hành"
    assert cleaner.clean_text("Họ và tên: ........\nđơn vị") == "Họ và tên: ........\nđơn vị"


def test_repeated_headers_footers_and_page_numbers_are_removed(tmp_path: Path) -> None:
    blocks = [
        DocumentBlock(block_id="h1", text="UBND TỈNH", page_number=1, source_order=0),
        DocumentBlock(block_id="p1", text="Nội dung trang một.", page_number=1, source_order=1),
        DocumentBlock(block_id="n1", text="1", page_number=1, source_order=2),
        DocumentBlock(block_id="h2", text="UBND TỈNH", page_number=2, source_order=3),
        DocumentBlock(block_id="p2", text="Nội dung trang hai.", page_number=2, source_order=4),
        DocumentBlock(block_id="n2", text="2", page_number=2, source_order=5),
    ]
    result = TextCleaner().clean(_document(tmp_path, blocks))
    assert [block.text for block in result.blocks] == ["Nội dung trang một.", "Nội dung trang hai."]
    assert {warning.code for warning in result.warnings} == {
        "repeated_page_edge_removed",
        "isolated_page_number_removed",
    }
