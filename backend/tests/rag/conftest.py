from pathlib import Path

import pytest

from app.rag.models import (
    BlockType,
    DocumentBlock,
    DocumentDomain,
    DocumentStatus,
    DocumentType,
    ParsedDocument,
    TableBlock,
)


@pytest.fixture
def parsed_document(tmp_path: Path) -> ParsedDocument:
    source = tmp_path / "law.pdf"
    source.write_bytes(b"test")
    return ParsedDocument(
        document_id="doc-test",
        document_name=source.name,
        source_path=source,
        mime_type="application/pdf",
        document_type=DocumentType.LEGAL,
        domain=DocumentDomain.POPULATION,
        document_status=DocumentStatus.ACTIVE,
        parser_name="test",
        blocks=[
            DocumentBlock(block_id="b0", text="Điều 1. Phạm vi", source_order=0),
            DocumentBlock(block_id="b1", text="1. Quy định thứ nhất.", source_order=1),
            DocumentBlock(block_id="b2", text="a) Nội dung chi tiết.", source_order=2),
            DocumentBlock(block_id="b3", text="Điều 2. Trách nhiệm", source_order=3),
            DocumentBlock(block_id="b4", text="Cơ quan thực hiện.", source_order=4),
        ],
    )


@pytest.fixture
def template_document(tmp_path: Path) -> ParsedDocument:
    source = tmp_path / "template.docx"
    source.write_bytes(b"test")
    return ParsedDocument(
        document_id="doc-template",
        document_name=source.name,
        source_path=source,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        document_type=DocumentType.TEMPLATE,
        domain=DocumentDomain.TASKS,
        parser_name="test",
        blocks=[
            DocumentBlock(
                block_id="b0",
                block_type=BlockType.TEMPLATE_SECTION,
                text="I. THÔNG TIN CHUNG",
                source_order=0,
            ),
            DocumentBlock(block_id="b1", text="Tên đơn vị: ........", source_order=1),
            DocumentBlock(
                block_id="b2",
                block_type=BlockType.TABLE,
                source_order=2,
                table=TableBlock(
                    name="Tiến độ", headers=["Nhiệm vụ", "Kết quả"], rows=[["A", "B"]]
                ),
            ),
        ],
    )
