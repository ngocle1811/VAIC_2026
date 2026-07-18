from pathlib import Path

import pytest

from app.rag.models import DocumentDomain, DocumentType
from app.rag.parsers.factory import ParserFactory
from app.rag.pipeline import RAGPhase1Pipeline


def test_complete_docx_phase1_pipeline(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    path = tmp_path / "guideline.docx"
    source = docx.Document()
    source.add_heading("QUY TRÌNH BÁO CÁO", level=1)
    source.add_paragraph("Bước thực hiện báo cáo định kỳ.")
    source.save(path)

    pipeline = RAGPhase1Pipeline(parser_factory=ParserFactory(prefer_docling=False))
    chunks = pipeline.process(
        path,
        document_type=DocumentType.GUIDELINE,
        domain=DocumentDomain.COMMON,
        document_id="guideline-test",
    )
    assert chunks
    chunk = chunks[0]
    assert chunk.chunk_id == "guideline-test-chunk-00000"
    assert chunk.document_name == "guideline.docx"
    assert chunk.document_type == DocumentType.GUIDELINE
    assert chunk.metadata.heading_hierarchy == ["QUY TRÌNH BÁO CÁO"]
