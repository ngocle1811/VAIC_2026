from app.llm.models import LLMRequest, LLMResponse


class FakeLLMClient:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self.responses:
            raise RuntimeError("FakeLLMClient has no scripted response")
        return self.responses.pop(0)
