"""Parser contract and shared source identity helpers."""

from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path

from app.rag.models import DocumentDomain, DocumentStatus, DocumentType, ParsedDocument


class BaseParser(ABC):
    """Replaceable interface implemented by every source parser."""

    supported_extensions: frozenset[str] = frozenset()
    parser_name = "base"

    def supports(self, source_path: str | Path) -> bool:
        return Path(source_path).suffix.lower() in self.supported_extensions

    @abstractmethod
    def parse(
        self,
        source_path: str | Path,
        *,
        document_type: DocumentType,
        domain: DocumentDomain = DocumentDomain.COMMON,
        document_status: DocumentStatus = DocumentStatus.UNKNOWN,
        document_id: str | None = None,
    ) -> ParsedDocument:
        """Parse a supported file into a validated neutral representation."""

    @staticmethod
    def source_id(path: Path) -> str:
        digest = sha256(path.read_bytes()).hexdigest()[:16]
        return f"doc-{digest}"
