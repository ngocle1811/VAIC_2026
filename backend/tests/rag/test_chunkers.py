from app.rag.chunkers.factory import ChunkerFactory
from app.rag.chunkers.guideline import GuidelineChunker
from app.rag.chunkers.legal import LegalDocumentChunker
from app.rag.chunkers.template import ReportTemplateChunker
from app.rag.models import BlockType, DocumentBlock, DocumentType
from app.rag.processing.structure import VietnameseStructureAnalyzer


def test_chunker_factory_selects_each_strategy() -> None:
    factory = ChunkerFactory()
    assert isinstance(factory.create(DocumentType.LEGAL), LegalDocumentChunker)
    assert isinstance(factory.create(DocumentType.GUIDELINE), GuidelineChunker)
    assert isinstance(factory.create(DocumentType.TEMPLATE), ReportTemplateChunker)


def test_legal_chunker_starts_at_article_boundaries(parsed_document) -> None:
    analyzed = VietnameseStructureAnalyzer().analyze(parsed_document)
    chunks = LegalDocumentChunker().chunk(analyzed)
    assert len(chunks) == 2
    assert chunks[0].metadata.article == "1"
    assert chunks[1].metadata.article == "2"
    assert chunks[0].chunk_id == "doc-test-chunk-00000"


def test_guideline_chunker_starts_at_headings(parsed_document) -> None:
    document = parsed_document.model_copy(
        update={
            "document_type": DocumentType.GUIDELINE,
            "blocks": [
                DocumentBlock(
                    block_id="h1", block_type=BlockType.HEADING, text="BƯỚC 1", source_order=0
                ),
                DocumentBlock(block_id="p1", text="Thực hiện nội dung.", source_order=1),
                DocumentBlock(
                    block_id="h2", block_type=BlockType.HEADING, text="BƯỚC 2", source_order=2
                ),
                DocumentBlock(block_id="p2", text="Hoàn tất nội dung.", source_order=3),
            ],
        }
    )
    chunks = GuidelineChunker().chunk(document)
    assert [chunk.content.splitlines()[0] for chunk in chunks] == ["BƯỚC 1", "BƯỚC 2"]


def test_template_chunker_isolates_tables(template_document) -> None:
    chunks = ReportTemplateChunker().chunk(template_document)
    assert len(chunks) == 2
    assert chunks[1].content == "Tiến độ\nNhiệm vụ | Kết quả\nA | B"
    assert chunks[1].metadata.table_name == "Tiến độ"
