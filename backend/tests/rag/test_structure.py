import pytest

from app.rag.models import BlockType, StructureKind
from app.rag.processing.structure import VietnameseStructureAnalyzer


@pytest.mark.parametrize(
    ("text", "kind", "identifier"),
    [
        ("PHẦN I QUY ĐỊNH CHUNG", StructureKind.PART, "I"),
        ("Chương II Trách nhiệm", StructureKind.CHAPTER, "II"),
        ("Mục 1 Phạm vi", StructureKind.SECTION, "1"),
        ("Điều 12a. Hiệu lực", StructureKind.ARTICLE, "12a"),
        ("2. Trách nhiệm thi hành", StructureKind.CLAUSE, "2"),
        ("đ) Nội dung cụ thể", StructureKind.POINT, "đ"),
        ("PHỤ LỤC I BIỂU MẪU", StructureKind.APPENDIX, "I"),
        ("I. THÔNG TIN CHUNG", StructureKind.TEMPLATE_SECTION, None),
    ],
)
def test_classifies_administrative_structure(text, kind, identifier) -> None:
    match = VietnameseStructureAnalyzer().classify(text)
    assert match is not None
    assert match.kind == kind
    assert match.identifier == identifier


def test_analysis_propagates_hierarchy_and_legal_context(parsed_document) -> None:
    analyzed = VietnameseStructureAnalyzer().analyze(parsed_document)
    assert analyzed.blocks[0].block_type == BlockType.ARTICLE
    assert analyzed.blocks[1].block_type == BlockType.CLAUSE
    assert analyzed.blocks[2].block_type == BlockType.POINT
    assert analyzed.blocks[2].article == "1"
    assert analyzed.blocks[2].clause == "1"
    assert analyzed.blocks[2].point == "a"
    assert analyzed.blocks[2].parent_block_id == "b1"
