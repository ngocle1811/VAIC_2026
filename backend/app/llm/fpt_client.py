"""Disabled-by-default FPT OpenAI-compatible chat-completions adapter."""

import json
import time
from collections.abc import Callable
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.config import Settings
from app.llm.models import LLMRequest, LLMResponse, LLMUsage, ToolCall
from app.security.content_guard import ExternalTransmissionGuard


class LLMProviderError(RuntimeError):
    pass


class FPTLLMClient:
    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
        guard: ExternalTransmissionGuard | None = None,
    ) -> None:
        if not settings.llm_enabled:
            raise LLMProviderError("LLM integration is disabled")
        api_key = settings.effective_llm_api_key
        base_url = settings.effective_llm_base_url
        if not api_key or not base_url:
            raise LLMProviderError("FPT LLM requires configured credentials and base URL")
        self.model_name = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.max_retries = settings.llm_max_retries
        self._sleep = sleep
        self._guard = guard or ExternalTransmissionGuard()
        self._client = client or OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        response = self._request(request)
        choices = getattr(response, "choices", None)
        if not choices:
            raise LLMProviderError("LLM returned no choices")
        message = choices[0].message
        content = getattr(message, "content", None)
        calls = []
        for call in getattr(message, "tool_calls", None) or []:
            try:
                arguments = json.loads(call.function.arguments)
            except (TypeError, json.JSONDecodeError) as exc:
                raise LLMProviderError("LLM tool arguments are invalid JSON") from exc
            calls.append(ToolCall(id=call.id, name=call.function.name, arguments=arguments))
        if not content and not calls:
            raise LLMProviderError("LLM returned an empty response")
        usage = getattr(response, "usage", None)
        return LLMResponse(
            content=content,
            tool_calls=calls,
            usage=(
                LLMUsage(
                    prompt_tokens=getattr(usage, "prompt_tokens", None),
                    completion_tokens=getattr(usage, "completion_tokens", None),
                    total_tokens=getattr(usage, "total_tokens", None),
                )
                if usage
                else None
            ),
        )

    def _request(self, request: LLMRequest) -> Any:
        messages = []
        for message in request.messages:
            decision = self._guard.inspect(message.content)
            if not decision.allowed:
                raise LLMProviderError("LLM transmission blocked by security policy")
            messages.append(
                message.model_copy(update={"content": decision.redacted_text}).model_dump(
                    exclude_none=True
                )
            )
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if request.tools:
            kwargs["tools"] = request.tools
        if request.structured_json:
            kwargs["response_format"] = {"type": "json_object"}
        for attempt in range(self.max_retries + 1):
            try:
                return self._client.chat.completions.create(**kwargs)
            except (APIConnectionError, APITimeoutError) as exc:
                retryable, error = True, exc
            except APIStatusError as exc:
                retryable, error = exc.status_code == 429 or exc.status_code >= 500, exc
            if not retryable or attempt >= self.max_retries:
                raise LLMProviderError(f"LLM request failed: {type(error).__name__}") from error
            self._sleep(min(2**attempt, 8))
        raise AssertionError("unreachable")
