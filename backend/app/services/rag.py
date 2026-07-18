"""Stable API and Agent-facing evidence retrieval service."""

from app.rag.retrieval.models import RAGSearchResult, RetrievalRequest
from app.rag.retrieval.pipeline import RetrievalPipeline


class RAGService:
    def __init__(self, pipeline: RetrievalPipeline) -> None:
        self.pipeline = pipeline

    def search(self, request: RetrievalRequest) -> RAGSearchResult:
        return self.pipeline.retrieve(request)
