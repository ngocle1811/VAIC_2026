from app.config import Settings
from app.llm.base import LLMClient
from app.llm.fake import FakeLLMClient
from app.llm.fpt_client import FPTLLMClient, LLMProviderError
from app.llm.models import LLMResponse


def create_llm_client(
    settings: Settings, *, fake_responses: list[LLMResponse] | None = None
) -> LLMClient:
    if settings.llm_provider == "fake":
        if fake_responses is None:
            raise LLMProviderError("Fake LLM requires explicit deterministic responses")
        return FakeLLMClient(fake_responses)
    if not settings.llm_enabled:
        raise LLMProviderError("LLM integration is disabled")
    return FPTLLMClient(settings)
