"""Provider-independent reranking contract."""

from typing import Protocol

from app.rag.retrieval.models import RerankedChunk, RetrievalCandidate


class Reranker(Protocol):
    model_name: str

    def rerank(
        self, query: str, candidates: list[RetrievalCandidate], top_k: int
    ) -> list[RerankedChunk]: ...
