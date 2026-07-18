"""Structural citation identity validation against a built retrieval context."""

from app.rag.retrieval.models import (
    BuiltContext,
    CitationReference,
    CitationValidationResult,
    RejectedCitation,
)


class CitationValidationError(ValueError):
    pass


class CitationValidator:
    def validate(
        self,
        citations: list[CitationReference],
        context: BuiltContext,
        *,
        strict: bool = False,
    ) -> CitationValidationResult:
        sources = {source.source_id: source for source in context.sources}
        accepted = []
        rejected = []
        rejected_keys: set[tuple[str, str]] = set()
        for citation in citations:
            source = sources.get(citation.source_id)
            reason = None
            if source is None:
                reason = "source_id was not retrieved"
            elif citation.chunk_id and citation.chunk_id != source.chunk_id:
                reason = "chunk_id does not match source"
            elif citation.document_id and citation.document_id != source.document_id:
                reason = "document_id does not match source"
            elif citation.document_name and citation.document_name != source.document_name:
                reason = "document_name does not match source"
            if reason:
                key = (citation.source_id, reason)
                if key not in rejected_keys:
                    rejected.append(RejectedCitation(citation=citation, reason=reason))
                    rejected_keys.add(key)
            elif citation not in accepted:
                accepted.append(citation)
        result = CitationValidationResult(valid=not rejected, accepted=accepted, rejected=rejected)
        if strict and rejected:
            raise CitationValidationError(rejected[0].reason)
        return result
