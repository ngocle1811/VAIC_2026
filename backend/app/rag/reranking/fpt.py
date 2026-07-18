"""Configurable reranker adapter without inventing an undocumented FPT endpoint."""

import math
import time
from collections.abc import Callable
from typing import Protocol

from app.rag.exceptions import RAGError
from app.rag.retrieval.models import RerankedChunk, RetrievalCandidate


class RerankerError(RAGError):
    pass


class RerankerTransportError(RerankerError):
    """Transport failure with an explicit retry classification."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class RerankerTransport(Protocol):
    def rerank(
        self, *, model: str, query: str, documents: list[str], timeout: float
    ) -> list[dict[str, object]]: ...


class ConfiguredFPTReranker:
    """Uses only an injected, documentation-verified transport."""

    def __init__(
        self,
        transport: RerankerTransport,
        *,
        model_name: str,
        timeout: float = 120,
        batch_size: int = 16,
        max_retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.transport = transport
        self.model_name = model_name
        self.timeout = timeout
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._sleep = sleep

    def _request(self, *, query: str, documents: list[str]) -> list[dict[str, object]]:
        for attempt in range(self.max_retries + 1):
            try:
                return self.transport.rerank(
                    model=self.model_name,
                    query=query,
                    documents=documents,
                    timeout=self.timeout,
                )
            except RerankerTransportError as exc:
                if not exc.retryable or attempt >= self.max_retries:
                    raise
                self._sleep(min(2**attempt, 8))
        raise AssertionError("unreachable")

    def rerank(
        self, query: str, candidates: list[RetrievalCandidate], top_k: int
    ) -> list[RerankedChunk]:
        indexed_scores: dict[int, float] = {}
        for start in range(0, len(candidates), self.batch_size):
            batch = candidates[start : start + self.batch_size]
            response = self._request(
                query=query, documents=[candidate.content for candidate in batch]
            )
            if len(response) != len(batch):
                raise RerankerError("Reranker returned an invalid score count")
            for item in response:
                index = item.get("index")
                score = item.get("score")
                if (
                    not isinstance(index, int)
                    or isinstance(score, bool)
                    or not isinstance(score, (int, float))
                ):
                    raise RerankerError("Reranker response is malformed")
                absolute_index = start + index
                numeric_score = float(score)
                if absolute_index in indexed_scores or not math.isfinite(numeric_score):
                    raise RerankerError("Reranker score is duplicate or non-finite")
                indexed_scores[absolute_index] = numeric_score
        if set(indexed_scores) != set(range(len(candidates))):
            raise RerankerError("Reranker response indices are incomplete")
        reranked = [
            RerankedChunk(
                **candidate.model_dump(exclude={"reranker_score", "retrieval_score"}),
                reranker_score=indexed_scores[index],
                retrieval_score=indexed_scores[index],
            )
            for index, candidate in enumerate(candidates)
        ]
        return sorted(reranked, key=lambda item: (-(item.reranker_score or 0.0), item.chunk_id))[
            :top_k
        ]
