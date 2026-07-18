"""Safe reranker fallback policy above any provider implementation."""

import logging

from app.rag.reranking.base import Reranker
from app.rag.retrieval.models import RerankedChunk, RetrievalCandidate

logger = logging.getLogger(__name__)


class RerankerService:
    def __init__(self, reranker: Reranker | None, *, strict: bool = False) -> None:
        self.reranker = reranker
        self.strict = strict

    def rerank(
        self, query: str, candidates: list[RetrievalCandidate], top_k: int
    ) -> tuple[list[RetrievalCandidate], list[str]]:
        if self.reranker is None:
            return candidates[:top_k], ["Reranker unavailable; retrieval ordering preserved."]
        try:
            return self.reranker.rerank(query, candidates, top_k), []
        except Exception:
            if self.strict:
                raise
            logger.exception("Reranker failed; preserving retrieval order")
            fallback = [RerankedChunk(**candidate.model_dump()) for candidate in candidates[:top_k]]
            return fallback, ["Reranker failed; retrieval ordering preserved."]
