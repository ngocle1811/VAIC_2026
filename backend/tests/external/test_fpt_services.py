"""These tests may consume paid APIs and are disabled unless explicitly enabled."""

import pytest

from app.config import Settings
from app.llm.fpt_client import FPTLLMClient
from app.llm.models import LLMMessage, LLMRequest
from app.rag.embeddings.fpt import FPTEmbeddingProvider

pytestmark = pytest.mark.external


@pytest.fixture(scope="module")
def external_settings() -> Settings:
    settings = Settings()
    if not settings.run_external_integration_tests:
        pytest.skip("RUN_EXTERNAL_INTEGRATION_TESTS is not enabled")
    return settings


def test_real_fpt_embedding_smoke(external_settings) -> None:
    vector = FPTEmbeddingProvider(external_settings).embed_query(
        "SYNTHETIC_TEST_DATA retrieval smoke test"
    )
    assert vector and all(isinstance(value, float) for value in vector)


def test_real_fpt_llm_smoke(external_settings) -> None:
    if not external_settings.llm_enabled:
        pytest.skip("LLM_ENABLED is not enabled")
    response = FPTLLMClient(external_settings).generate(
        LLMRequest(
            messages=[
                LLMMessage(
                    role="user",
                    content="Return exactly the token SYNTHETIC_TEST_DATA.",
                )
            ]
        )
    )
    assert response.content
