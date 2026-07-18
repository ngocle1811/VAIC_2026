"""Managed, traversal-safe storage for original Knowledge Base files."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from app.rag.exceptions import RAGError, UnsupportedDocumentError

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".docx"})
SUPPORTED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    }
)


class FileStorageError(RAGError):
    """Raised when a source cannot be safely stored."""


@dataclass(frozen=True, slots=True)
class StoredDocument:
    original_filename: str
    stored_filename: str
    file_path: Path
    file_type: str
    mime_type: str
    file_size_bytes: int
    checksum_sha256: str


class KnowledgeBaseStorage:
    def __init__(self, originals_dir: Path, max_size_mb: int = 50) -> None:
        self.originals_dir = originals_dir.resolve()
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def inspect(self, source_path: str | Path, mime_type: str | None = None) -> StoredDocument:
        source = Path(source_path).resolve()
        if not source.is_file():
            raise FileStorageError(f"Source file does not exist: {source}")
        extension = source.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedDocumentError(f"Unsupported document extension: {extension}")
        size = source.stat().st_size
        if size > self.max_size_bytes:
            raise FileStorageError(
                f"Document size {size} exceeds configured maximum {self.max_size_bytes} bytes"
            )
        detected_mime = (
            mime_type or mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        )
        if detected_mime not in SUPPORTED_MIME_TYPES:
            raise FileStorageError(f"Unsupported MIME type: {detected_mime}")
        checksum = self._checksum(source)
        safe_name = self._safe_filename(source.name)
        return StoredDocument(
            original_filename=source.name,
            stored_filename=safe_name,
            file_path=source,
            file_type=extension.lstrip("."),
            mime_type=detected_mime,
            file_size_bytes=size,
            checksum_sha256=checksum,
        )

    def store(
        self, source_path: str | Path, document_id: str, mime_type: str | None = None
    ) -> StoredDocument:
        inspected = self.inspect(source_path, mime_type)
        safe_document_id = re.sub(r"[^A-Za-z0-9_-]", "_", document_id)
        target_dir = (self.originals_dir / safe_document_id).resolve()
        if self.originals_dir not in target_dir.parents:
            raise FileStorageError("Resolved storage path escapes the configured root")
        target_dir.mkdir(parents=True, exist_ok=True)
        target = (target_dir / inspected.stored_filename).resolve()
        if target_dir not in target.parents:
            raise FileStorageError("Resolved file path escapes the document directory")
        if target.exists():
            raise FileStorageError(f"Managed original already exists: {target.name}")
        shutil.copy2(inspected.file_path, target)
        return StoredDocument(
            original_filename=inspected.original_filename,
            stored_filename=inspected.stored_filename,
            file_path=target,
            file_type=inspected.file_type,
            mime_type=inspected.mime_type,
            file_size_bytes=inspected.file_size_bytes,
            checksum_sha256=inspected.checksum_sha256,
        )

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for data in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(data)
        return digest.hexdigest()

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = Path(filename).name
        stem = unicodedata.normalize("NFKD", Path(name).stem).encode("ascii", "ignore").decode()
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "document"
        return f"{stem[:180]}{Path(name).suffix.lower()}"
