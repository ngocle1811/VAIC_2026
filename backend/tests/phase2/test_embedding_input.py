from app.rag.embeddings.input_builder import build_embedding_input
from app.rag.models import (
    ChunkMetadata,
    DocumentChunk,
    DocumentDomain,
    DocumentStatus,
    DocumentType,
)


def test_embedding_input_is_deterministic_and_safe(tmp_path) -> None:
    chunk = DocumentChunk(
        chunk_id="c1",
        document_id="d1",
        document_name="Nghị định 09",
        document_type=DocumentType.LEGAL,
        domain=DocumentDomain.COMMON,
        document_status=DocumentStatus.ACTIVE,
        chunk_index=0,
        content="Quy định báo cáo.",
        metadata=ChunkMetadata(
            source_path=str(tmp_path.resolve() / "secret.pdf"),
            parser_name="test",
            heading_hierarchy=["CHƯƠNG II"],
            article="8",
            clause="2",
        ),
    )
    first = build_embedding_input(chunk)
    assert first == build_embedding_input(chunk)
    assert "CHƯƠNG II" in first and "Article: 8" in first and chunk.content in first
    assert str(tmp_path.resolve()) not in first
    assert "parser_name" not in first
