"""Explicit RAG Phase 1 exceptions."""


class RAGError(Exception):
    """Base exception for Phase 1 RAG processing."""


class UnsupportedDocumentError(RAGError):
    """Raised when no parser supports a source document."""


class DocumentParsingError(RAGError):
    """Raised when a supported document cannot be parsed."""


class OptionalParserUnavailableError(RAGError):
    """Raised when an explicitly selected optional parser is unavailable."""


class ChunkingError(RAGError):
    """Raised when a parsed document cannot be chunked."""
