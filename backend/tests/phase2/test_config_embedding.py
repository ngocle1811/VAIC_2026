from types import SimpleNamespace

import httpx
import pytest
from openai import APIStatusError

from app.config import Settings
from app.rag.embeddings.fpt import EmbeddingProviderError, FPTEmbeddingProvider
from app.rag.embeddings.service import EmbeddingService


def test_missing_credentials_do_not_break_settings_import() -> None:
    settings = Settings(_env_file=None, fpt_api_key=None, fpt_base_url=None)
    assert settings.embedding_model == "Vietnamese_Embedding"
    with pytest.raises(EmbeddingProviderError):
        FPTEmbeddingProvider(settings)


def test_embedding_credentials_override_common_credentials() -> None:
    settings = Settings(
        _env_file=None,
        fpt_api_key="common-key",
        fpt_base_url="https://common.invalid/v1",
        fpt_embedding_api_key="embedding-key",
        fpt_embedding_base_url="https://embedding.invalid/v1",
    )
    assert settings.effective_embedding_api_key == "embedding-key"
    assert settings.effective_embedding_base_url == "https://embedding.invalid/v1"


def test_fpt_provider_empty_inputs_do_not_call_client() -> None:
    client = SimpleNamespace(embeddings=SimpleNamespace(create=lambda **kwargs: pytest.fail()))
    provider = FPTEmbeddingProvider(
        Settings(_env_file=None, fpt_api_key="key", fpt_base_url="https://example.invalid/v1"),
        client=client,
    )
    assert provider.embed_documents([]) == []
    with pytest.raises(EmbeddingProviderError):
        provider.embed_query("  ")


@pytest.mark.parametrize(
    "data",
    [
        [],
        [SimpleNamespace(index=0, embedding=[])],
        [SimpleNamespace(index=0, embedding=[1, "bad"])],
        [SimpleNamespace(index=0, embedding=[1, float("inf")])],
        [
            SimpleNamespace(index=0, embedding=[1, 2]),
            SimpleNamespace(index=1, embedding=[1]),
        ],
    ],
)
def test_fpt_provider_rejects_malformed_vectors(data) -> None:
    with pytest.raises(EmbeddingProviderError):
        FPTEmbeddingProvider._validate_response(SimpleNamespace(data=data), max(1, len(data)))


def test_fpt_provider_preserves_response_index_order() -> None:
    response = SimpleNamespace(
        data=[
            SimpleNamespace(index=1, embedding=[3, 4]),
            SimpleNamespace(index=0, embedding=[1, 2]),
        ]
    )
    assert FPTEmbeddingProvider._validate_response(response, 2) == [[1.0, 2.0], [3.0, 4.0]]


def test_embedding_service_splits_batches(fake_provider) -> None:
    service = EmbeddingService(fake_provider, batch_size=2, normalize=False)
    assert len(service.embed_documents(["a", "b", "c", "d", "e"])) == 5
    assert fake_provider.document_calls == 3


class _RetryClient:
    def __init__(self, status_codes: list[int]) -> None:
        self.status_codes = status_codes
        self.calls = 0
        self.embeddings = self

    def create(self, **kwargs):
        status = self.status_codes[min(self.calls, len(self.status_codes) - 1)]
        self.calls += 1
        if status >= 400:
            request = httpx.Request("POST", "https://example.invalid/v1/embeddings")
            response = httpx.Response(status, request=request)
            raise APIStatusError("provider error", response=response, body=None)
        return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[1.0, 2.0])])


def _retry_provider(client: _RetryClient, sleeps: list[float]) -> FPTEmbeddingProvider:
    return FPTEmbeddingProvider(
        Settings(
            _env_file=None,
            fpt_api_key="key",
            fpt_base_url="https://example.invalid/v1",
            embedding_max_retries=2,
        ),
        client=client,
        sleep=sleeps.append,
    )


def test_fpt_provider_retries_retryable_status() -> None:
    client = _RetryClient([429, 500, 200])
    sleeps: list[float] = []
    assert _retry_provider(client, sleeps).embed_documents(["short input"]) == [[1.0, 2.0]]
    assert client.calls == 3
    assert sleeps == [1, 2]


def test_fpt_provider_does_not_retry_permanent_status() -> None:
    client = _RetryClient([400])
    sleeps: list[float] = []
    with pytest.raises(EmbeddingProviderError):
        _retry_provider(client, sleeps).embed_documents(["short input"])
    assert client.calls == 1
    assert sleeps == []


def test_embedding_provider_masks_pii_and_blocks_restricted_content() -> None:
    captured = {}

    class Client:
        embeddings = None

        def __init__(self):
            self.embeddings = self

        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[1.0, 2.0])])

    provider = FPTEmbeddingProvider(
        Settings(_env_file=None, fpt_api_key="key", fpt_base_url="https://example.invalid/v1"),
        client=Client(),
    )
    provider.embed_query("0901234567")
    assert "0901234567" not in captured["input"][0]
    with pytest.raises(EmbeddingProviderError, match="security policy"):
        provider.embed_query("MẬT")
