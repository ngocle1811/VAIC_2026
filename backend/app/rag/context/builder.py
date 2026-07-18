"""Deterministic evidence context rendering with stable source labels."""

import re

from app.rag.context.token_budget import estimate_tokens
from app.rag.retrieval.models import BuiltContext, ContextSource, RetrievalCandidate


class ContextBuilder:
    def __init__(self, max_tokens: int = 6000) -> None:
        self.max_tokens = max_tokens

    def build(self, candidates: list[RetrievalCandidate]) -> BuiltContext:
        blocks: list[str] = []
        sources: list[ContextSource] = []
        seen_chunks: set[str] = set()
        seen_content: set[str] = set()
        used_tokens = 0
        truncated = False
        for candidate in candidates:
            fingerprint = re.sub(r"\s+", " ", candidate.content).strip().casefold()
            if candidate.chunk_id in seen_chunks or fingerprint in seen_content:
                continue
            source = self._source(candidate, len(sources) + 1)
            rendered = self._render(source)
            cost = estimate_tokens(rendered)
            if used_tokens + cost > self.max_tokens:
                truncated = True
                continue
            seen_chunks.add(candidate.chunk_id)
            seen_content.add(fingerprint)
            sources.append(source)
            blocks.append(rendered)
            used_tokens += cost
        warnings = ["Context truncated to configured token budget."] if truncated else []
        return BuiltContext(
            text="\n\n".join(blocks),
            sources=sources,
            estimated_tokens=used_tokens,
            truncated=truncated,
            warnings=warnings,
        )

    @staticmethod
    def _source(candidate: RetrievalCandidate, number: int) -> ContextSource:
        metadata = candidate.metadata
        hierarchy = metadata.get("heading_hierarchy") or []
        hierarchy = hierarchy if isinstance(hierarchy, list) else []
        page_numbers = metadata.get("page_numbers") or []
        page_number = page_numbers[0] if isinstance(page_numbers, list) and page_numbers else None
        return ContextSource(
            source_id=f"SOURCE_{number}",
            chunk_id=candidate.chunk_id,
            document_id=candidate.document_id,
            document_name=candidate.document_name,
            document_number=_optional(metadata.get("document_number")),
            document_type=candidate.document_type,
            domain=candidate.domain,
            source=_optional(metadata.get("source")),
            chapter=next(
                (str(item) for item in hierarchy if str(item).upper().startswith("CH")), None
            ),
            section=next(
                (str(item) for item in hierarchy if str(item).upper().startswith("M")), None
            ),
            article=_optional(metadata.get("article")),
            clause=_optional(metadata.get("clause")),
            point=_optional(metadata.get("point")),
            heading=str(hierarchy[-1]) if hierarchy else None,
            page_number=int(page_number) if isinstance(page_number, int) else None,
            retrieval_score=candidate.retrieval_score,
            dense_score=candidate.dense_score,
            lexical_score=candidate.lexical_score,
            fused_score=candidate.fused_score,
            reranker_score=candidate.reranker_score,
            content=candidate.content,
        )

    @staticmethod
    def _render(source: ContextSource) -> str:
        lines = [
            f"[{source.source_id}]",
            f"Document ID: {source.document_id}",
            f"Document: {source.document_name}",
            f"Document number: {source.document_number or ''}",
        ]
        location = ", ".join(
            value
            for value in (
                source.chapter,
                source.section,
                f"Điều {source.article}" if source.article else None,
                f"Khoản {source.clause}" if source.clause else None,
                f"Điểm {source.point}" if source.point else None,
            )
            if value
        )
        lines.extend(
            (
                f"Location: {location}",
                f"Page: {source.page_number or ''}",
                f"Chunk ID: {source.chunk_id}",
                "Content:",
                source.content,
            )
        )
        return "\n".join(lines)


def _optional(value: object) -> str | None:
    return str(value) if value is not None else None
