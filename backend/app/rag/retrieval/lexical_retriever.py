"""Cached in-process BM25 retrieval for the current small Knowledge Base."""

import math
import re
import unicodedata
from collections import Counter

from app.rag.retrieval.corpus import ChunkCorpusSource
from app.rag.retrieval.models import LexicalSearchResult, RetrievalFilters, SearchableChunk

_TOKEN = re.compile(r"[\wÀ-ỹ]+(?:[./-][\wÀ-ỹ]+)*", re.UNICODE)


def tokenize_vietnamese(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN.findall(unicodedata.normalize("NFC", text))]


class BM25Retriever:
    """MVP in-process BM25; refresh explicitly after the corpus changes."""

    def __init__(self, corpus: ChunkCorpusSource, *, k1: float = 1.5, b: float = 0.75) -> None:
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self._cache_key: str | None = None
        self._documents: list[SearchableChunk] = []
        self._tokens: list[list[str]] = []
        self.build_count = 0

    def invalidate(self) -> None:
        self._cache_key = None

    def search(
        self, query: str, filters: RetrievalFilters, top_k: int
    ) -> list[LexicalSearchResult]:
        query_tokens = tokenize_vietnamese(query)
        if not query_tokens or top_k < 1:
            return []
        self._ensure_index(filters)
        if not self._documents:
            return []
        document_frequency = Counter(token for tokens in self._tokens for token in set(tokens))
        average_length = sum(map(len, self._tokens)) / len(self._tokens) or 1.0
        scored = []
        for chunk, tokens in zip(self._documents, self._tokens, strict=True):
            frequencies = Counter(tokens)
            score = 0.0
            for token in query_tokens:
                frequency = frequencies[token]
                if not frequency:
                    continue
                count = len(self._documents)
                idf = math.log(
                    1
                    + (count - document_frequency[token] + 0.5) / (document_frequency[token] + 0.5)
                )
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * len(tokens) / average_length
                )
                score += idf * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scored.append(
                    LexicalSearchResult(
                        **chunk.model_dump(),
                        retrieval_score=score,
                        lexical_score=score,
                    )
                )
        return sorted(scored, key=lambda item: (-item.retrieval_score, item.chunk_id))[:top_k]

    def _ensure_index(self, filters: RetrievalFilters) -> None:
        cache_key = f"{self.corpus.version}:{filters.model_dump_json()}"
        if cache_key == self._cache_key:
            return
        self._documents = self.corpus.list_searchable_chunks(filters)
        self._tokens = [
            tokenize_vietnamese(
                " ".join(
                    (
                        chunk.document_name,
                        str(chunk.metadata.get("document_number", "")),
                        chunk.content,
                    )
                )
            )
            for chunk in self._documents
        ]
        self._cache_key = cache_key
        self.build_count += 1
