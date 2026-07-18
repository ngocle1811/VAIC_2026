"""Optional parent chunk lookup behind the corpus abstraction."""

from app.rag.retrieval.corpus import ChunkCorpusSource
from app.rag.retrieval.models import RetrievalCandidate


class ParentContextExpander:
    def __init__(self, corpus: ChunkCorpusSource) -> None:
        self.corpus = corpus

    def expand(
        self, candidates: list[RetrievalCandidate], max_tokens: int
    ) -> tuple[list[RetrievalCandidate], list[str]]:
        expanded: list[RetrievalCandidate] = []
        seen = {candidate.chunk_id for candidate in candidates}
        used = sum(_estimate(candidate.content) for candidate in candidates)
        warnings = []
        for candidate in candidates:
            expanded.append(candidate)
            parent_id = candidate.metadata.get("parent_chunk_id")
            if not isinstance(parent_id, str) or parent_id in seen:
                continue
            parent = self.corpus.get_chunk(candidate.document_id, parent_id)
            if parent is None:
                warnings.append(f"Parent chunk unavailable for {candidate.chunk_id}")
                continue
            cost = _estimate(parent.content)
            if used + cost > max_tokens:
                warnings.append(f"Parent chunk omitted by token budget for {candidate.chunk_id}")
                continue
            expanded.append(
                RetrievalCandidate(
                    **parent.model_dump(),
                    retrieval_score=candidate.retrieval_score,
                    dense_score=candidate.dense_score,
                    lexical_score=candidate.lexical_score,
                    fused_score=candidate.fused_score,
                    reranker_score=candidate.reranker_score,
                )
            )
            seen.add(parent_id)
            used += cost
        return expanded, warnings


def _estimate(text: str) -> int:
    return max(1, (len(text) + 3) // 4)
