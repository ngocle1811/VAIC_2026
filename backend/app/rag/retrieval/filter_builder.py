"""Build provider-neutral metadata constraints with active-document defaults."""

from app.rag.retrieval.models import RetrievalFilters, RetrievalRequest


class MetadataFilterBuilder:
    def __init__(self, default_document_status: str = "active") -> None:
        self.default_document_status = default_document_status

    def build(self, request: RetrievalRequest) -> RetrievalFilters:
        return RetrievalFilters(
            domain=request.domain.value if request.domain else None,
            document_types=[item.value for item in request.document_types],
            document_ids=request.document_ids,
            document_status=(
                request.document_status.value
                if request.document_status
                else self.default_document_status
            ),
            source=request.source,
            document_number=request.document_number,
            effective_on=request.effective_on,
        )
