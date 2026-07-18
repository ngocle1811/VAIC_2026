"""FPT AI Factory embedding provider using the OpenAI-compatible API."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.config import Settings
from app.rag.exceptions import RAGError
from app.security.content_guard import ExternalTransmissionGuard

logger = logging.getLogger(__name__)


class EmbeddingProviderError(RAGError):
    """Raised for invalid configuration or malformed embedding responses."""


class FPTEmbeddingProvider:
    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
        guard: ExternalTransmissionGuard | None = None,
    ) -> None:
        api_key = settings.effective_embedding_api_key
        base_url = settings.effective_embedding_base_url
        if not api_key or not base_url:
            raise EmbeddingProviderError(
                "FPT embedding credentials require an API key and exact configured base URL"
            )
        self.model_name = settings.embedding_model
        self.max_retries = settings.embedding_max_retries
        self._sleep = sleep
        self._guard = guard or ExternalTransmissionGuard()
        self._client = client or OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=settings.embedding_timeout_seconds,
            max_retries=0,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise EmbeddingProviderError("embedding document inputs must not be empty")
        response = self._request(texts)
        return self._validate_response(response, len(texts))

    def embed_query(self, query: str) -> list[float]:
        if not query.strip():
            raise EmbeddingProviderError("embedding query must not be empty")
        return self.embed_documents([query])[0]

    def _request(self, texts: list[str]) -> Any:
        safe_texts = []
        for text in texts:
            decision = self._guard.inspect(text)
            if not decision.allowed:
                raise EmbeddingProviderError("Embedding transmission blocked by security policy")
            safe_texts.append(decision.redacted_text)
        for attempt in range(self.max_retries + 1):
            try:
                return self._client.embeddings.create(model=self.model_name, input=safe_texts)
            except (APIConnectionError, APITimeoutError) as exc:
                retryable = True
                error = exc
            except APIStatusError as exc:
                retryable = exc.status_code == 429 or exc.status_code >= 500
                error = exc
            if not retryable or attempt >= self.max_retries:
                raise EmbeddingProviderError(
                    f"Embedding provider request failed: {type(error).__name__}"
                ) from error
            delay = min(2**attempt, 8)
            logger.warning("Retrying embedding request", extra={"attempt": attempt + 1})
            self._sleep(delay)
        raise AssertionError("unreachable")

    @staticmethod
    def _validate_response(response: Any, expected_count: int) -> list[list[float]]:
        data = getattr(response, "data", None)
        if not isinstance(data, list) or len(data) != expected_count:
            raise EmbeddingProviderError("Embedding provider returned an invalid vector count")
        indexed: dict[int, list[float]] = {}
        dimension: int | None = None
        for item in data:
            index = getattr(item, "index", None)
            raw_vector = getattr(item, "embedding", None)
            if not isinstance(index, int) or index in indexed or not isinstance(raw_vector, list):
                raise EmbeddingProviderError("Embedding provider response is malformed")
            if not raw_vector:
                raise EmbeddingProviderError("Embedding provider returned an empty vector")
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                for value in raw_vector
            ):
                raise EmbeddingProviderError("Embedding vector contains a non-numeric value")
            vector = [float(value) for value in raw_vector]
            if any(not math.isfinite(value) for value in vector):
                raise EmbeddingProviderError("Embedding vector contains a non-finite value")
            dimension = dimension or len(vector)
            if len(vector) != dimension:
                raise EmbeddingProviderError("Embedding vectors have inconsistent dimensions")
            indexed[index] = vector
        if set(indexed) != set(range(expected_count)):
            raise EmbeddingProviderError("Embedding response indices are incomplete")
        return [indexed[index] for index in range(expected_count)]
