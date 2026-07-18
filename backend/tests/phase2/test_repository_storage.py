import hashlib
from pathlib import Path

import pytest

from app.models.knowledge_document import ProcessingStatus
from app.rag.exceptions import UnsupportedDocumentError
from app.repositories.knowledge_document_repository import KnowledgeDocumentRepository
from app.services.knowledge_base_storage import FileStorageError, KnowledgeBaseStorage


def _values(source: Path) -> dict[str, object]:
    return {
        "id": "doc-1",
        "original_filename": source.name,
        "stored_filename": source.name,
        "file_path": str(source),
        "file_type": "pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": source.stat().st_size,
        "checksum_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "document_name": "Document",
        "document_type": "legal",
        "domain": "common",
        "document_status": "active",
        "processing_status": ProcessingStatus.UPLOADED,
    }


def test_repository_lifecycle_and_filters(db_session, tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"pdf")
    repository = KnowledgeDocumentRepository(db_session)
    document = repository.create_document(**_values(source))
    assert repository.get_by_checksum(document.checksum_sha256) == document
    repository.mark_processing(document)
    assert document.processing_status == ProcessingStatus.PROCESSING
    repository.mark_ready(
        document, provider="fpt", model="Vietnamese_Embedding", dimension=4, chunk_count=3
    )
    assert repository.list_documents(domain="common") == [document]
    repository.mark_failed(document, "embedding", "failure")
    assert document.failed_stage == "embedding"
    repository.mark_deleted(document)
    assert document.processing_status == ProcessingStatus.DELETED


def test_storage_is_safe_and_preserves_source(tmp_path: Path) -> None:
    source = tmp_path / "../../unsafe name.pdf"
    source = tmp_path / "unsafe name.pdf"
    source.write_bytes(b"original")
    storage = KnowledgeBaseStorage(tmp_path / "storage")
    stored = storage.store(source, "doc/../1")
    assert stored.stored_filename == "unsafe_name.pdf"
    assert stored.checksum_sha256 == hashlib.sha256(b"original").hexdigest()
    assert source.read_bytes() == b"original"
    assert stored.file_path.read_bytes() == b"original"
    with pytest.raises(FileStorageError):
        storage.store(source, "doc/../1")


def test_storage_rejects_size_and_extension(tmp_path: Path) -> None:
    text = tmp_path / "bad.txt"
    text.write_text("bad")
    storage = KnowledgeBaseStorage(tmp_path / "storage", max_size_mb=1)
    with pytest.raises(UnsupportedDocumentError):
        storage.inspect(text)
    large = tmp_path / "large.pdf"
    large.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(FileStorageError):
        storage.inspect(large)
