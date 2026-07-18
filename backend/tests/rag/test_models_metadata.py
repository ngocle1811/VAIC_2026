from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rag.config import ChunkingConfig
from app.rag.metadata import MetadataBuilder
from app.rag.models import BlockType, DocumentBlock, TableBlock


def test_table_block_validates_width() -> None:
    with pytest.raises(ValidationError):
        TableBlock(headers=["one"], rows=[["one", "two"]])


def test_document_block_requires_table_payload() -> None:
    with pytest.raises(ValidationError):
        DocumentBlock(block_id="x", block_type=BlockType.TABLE, source_order=0)


def test_chunking_config_rejects_invalid_relationships() -> None:
    with pytest.raises(ValidationError):
        ChunkingConfig(target_size=500, max_size=400)
    with pytest.raises(ValidationError):
        ChunkingConfig(target_size=500, max_size=600, overlap=500)


def test_metadata_builder_preserves_source_context(parsed_document) -> None:
    blocks = [
        block.model_copy(
            update={
                "page_number": 2,
                "heading_hierarchy": ["CHƯƠNG I", "Điều 1"],
                "article": "1",
                "parent_block_id": "chapter-1",
            }
        )
        for block in parsed_document.blocks[:2]
    ]
    metadata = MetadataBuilder().build(parsed_document, blocks)
    assert metadata.source_path == str(Path(parsed_document.source_path))
    assert metadata.page_numbers == [2]
    assert metadata.article == "1"
    assert metadata.heading_hierarchy[-1] == "Điều 1"
    assert metadata.parent_block_id == "chapter-1"
