from typing import Protocol

from app.llm.models import LLMRequest, LLMResponse


class LLMClient(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
