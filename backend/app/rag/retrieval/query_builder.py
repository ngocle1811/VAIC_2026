"""Deterministic Vietnamese query normalization and identifier detection."""

import re
import unicodedata
from typing import Protocol

from app.rag.retrieval.models import RetrievalRequest

_IDENTIFIERS = re.compile(
    r"\b\d{1,4}/\d{4}/[A-ZĐ-]+\b|\b(?:Điều|Khoản)\s+\d+[a-zđ]?\b|\bMẫu\s+số\s+\d+\b",
    re.I,
)


class QueryRewriter(Protocol):
    def rewrite(self, query: str) -> str: ...


class DeterministicQueryBuilder:
    def normalize(self, query: str) -> str:
        normalized = unicodedata.normalize("NFC", query).replace("\u00a0", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            raise ValueError("retrieval query must not be blank")
        return normalized

    def identifiers(self, normalized_query: str) -> list[str]:
        return list(
            dict.fromkeys(match.group(0) for match in _IDENTIFIERS.finditer(normalized_query))
        )

    def build(self, request: RetrievalRequest) -> tuple[str, list[str]]:
        normalized = self.normalize(request.query)
        return normalized, self.identifiers(normalized)
