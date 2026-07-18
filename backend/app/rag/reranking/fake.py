"""Deterministic fake reranker for default tests and disabled infrastructure."""

from app.rag.retrieval.lexical_retriever import tokenize_vietnamese
from app.rag.retrieval.models import RerankedChunk, RetrievalCandidate


class FakeReranker:
    model_name = "fake-reranker"

    def rerank(
        self, query: str, candidates: list[RetrievalCandidate], top_k: int
    ) -> list[RerankedChunk]:
        query_tokens = set(tokenize_vietnamese(query))
        reranked = []
        for candidate in candidates:
            content_tokens = set(tokenize_vietnamese(candidate.content))
            score = float(len(query_tokens & content_tokens))
            reranked.append(
                RerankedChunk(
                    **candidate.model_dump(exclude={"reranker_score", "retrieval_score"}),
                    reranker_score=score,
                    retrieval_score=score,
                )
            )
        return sorted(
            reranked,
            key=lambda item: (
                -(item.reranker_score or 0.0),
                -(item.fused_score or item.dense_score or item.lexical_score or 0.0),
                item.chunk_id,
            ),
        )[:top_k]
