"""Reciprocal Rank Fusion without cross-score normalization assumptions."""

from app.rag.retrieval.models import FusedSearchResult, RetrievalCandidate


def reciprocal_rank_fusion(
    dense: list[RetrievalCandidate],
    lexical: list[RetrievalCandidate],
    *,
    rrf_k: int = 60,
    dense_weight: float = 1.0,
    lexical_weight: float = 1.0,
) -> list[FusedSearchResult]:
    merged: dict[str, FusedSearchResult] = {}
    for results, score_field, weight in (
        (dense, "dense_score", dense_weight),
        (lexical, "lexical_score", lexical_weight),
    ):
        for rank, candidate in enumerate(results, 1):
            existing = merged.get(candidate.chunk_id)
            if existing is None:
                existing = FusedSearchResult(**candidate.model_dump())
                existing.fused_score = 0.0
                merged[candidate.chunk_id] = existing
            setattr(existing, score_field, getattr(candidate, score_field))
            existing.fused_score = (existing.fused_score or 0.0) + weight / (rrf_k + rank)
            existing.retrieval_score = existing.fused_score
    return sorted(merged.values(), key=lambda item: (-(item.fused_score or 0.0), item.chunk_id))
