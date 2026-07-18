from types import SimpleNamespace

import httpx
import pytest
from openai import APIStatusError
from pydantic import BaseModel

from app.agent.models import AgentExecutionContext, ToolResult
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.future_contracts import (
    fake_data_query_tool,
    fake_kpi_tool,
    fake_report_export_tool,
    fake_rule_engine_tool,
)
from app.agent.tools.rag_search_tool import RAGSearchTool
from app.config import Settings
from app.llm.fake import FakeLLMClient
from app.llm.fpt_client import FPTLLMClient, LLMProviderError
from app.llm.models import LLMMessage, LLMRequest, LLMResponse
from app.rag.retrieval.models import ContextSource, RAGSearchResult


def test_llm_disabled_import_fake_and_fpt_response() -> None:
    settings = Settings(_env_file=None)
    with pytest.raises(LLMProviderError, match="disabled"):
        FPTLLMClient(settings)
    fake = FakeLLMClient([LLMResponse(content="ok")])
    assert (
        fake.generate(LLMRequest(messages=[LLMMessage(role="user", content="hi")])).content == "ok"
    )

    message = SimpleNamespace(content='{"ok": true}', tool_calls=[])
    response = SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response))
    )
    enabled = Settings(
        _env_file=None,
        llm_enabled=True,
        fpt_llm_api_key="key",
        fpt_llm_base_url="https://example.invalid/v1",
    )
    result = FPTLLMClient(enabled, client=client).generate(
        LLMRequest(messages=[LLMMessage(role="user", content="hi")], structured_json=True)
    )
    assert result.content == '{"ok": true}'


def _status_error(status_code: int) -> APIStatusError:
    request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return APIStatusError("failure", response=response, body=None)


def test_fpt_llm_retry_permanent_error_and_empty_response() -> None:
    success = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=[]))],
        usage=None,
    )

    class Completion:
        def __init__(self, outcomes):
            self.outcomes = iter(outcomes)
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            outcome = next(self.outcomes)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    settings = Settings(
        _env_file=None,
        llm_enabled=True,
        fpt_llm_api_key="key",
        fpt_llm_base_url="https://example.invalid/v1",
        llm_max_retries=1,
    )
    completion = Completion([_status_error(429), success])
    client = SimpleNamespace(chat=SimpleNamespace(completions=completion))
    result = FPTLLMClient(settings, client=client, sleep=lambda _: None).generate(
        LLMRequest(messages=[LLMMessage(role="user", content="hi")])
    )
    assert result.content == "ok" and completion.calls == 2

    permanent = Completion([_status_error(400)])
    client = SimpleNamespace(chat=SimpleNamespace(completions=permanent))
    with pytest.raises(LLMProviderError, match="APIStatusError"):
        FPTLLMClient(settings, client=client, sleep=lambda _: None).generate(
            LLMRequest(messages=[LLMMessage(role="user", content="hi")])
        )
    assert permanent.calls == 1

    empty = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[]))],
        usage=None,
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: empty))
    )
    with pytest.raises(LLMProviderError, match="empty response"):
        FPTLLMClient(settings, client=client).generate(
            LLMRequest(messages=[LLMMessage(role="user", content="hi")])
        )


def test_fpt_llm_masks_pii_and_blocks_restricted_content() -> None:
    captured = {}
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=[]))],
        usage=None,
    )

    def create(**kwargs):
        captured.update(kwargs)
        return response

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    settings = Settings(
        _env_file=None,
        llm_enabled=True,
        fpt_llm_api_key="key",
        fpt_llm_base_url="https://example.invalid/v1",
    )
    llm = FPTLLMClient(settings, client=client)
    llm.generate(LLMRequest(messages=[LLMMessage(role="user", content="0901234567")]))
    assert "0901234567" not in captured["messages"][0]["content"]
    with pytest.raises(LLMProviderError, match="security policy"):
        llm.generate(LLMRequest(messages=[LLMMessage(role="user", content="MẬT")]))


class Input(BaseModel):
    value: int


class Tool:
    name = "test"
    description = "test tool"
    input_model = Input

    def execute(self, arguments, context):
        return ToolResult(success=True, data={"value": arguments.value})


def test_tool_registry_validation_errors_and_duplicates() -> None:
    registry = ToolRegistry()
    registry.register(Tool())
    assert registry.definitions()[0].name == "test"
    with pytest.raises(ValueError):
        registry.register(Tool())
    context = AgentExecutionContext(request_id="r")
    assert registry.execute("test", {"value": 2}, context).data == {"value": 2}
    assert registry.execute("test", {"value": "bad"}, context).error.code == "invalid_arguments"
    assert registry.execute("missing", {}, context).error.code == "unknown_tool"


class StubRAG:
    def search(self, request):
        source = ContextSource(
            source_id="SOURCE_1",
            chunk_id="c1",
            document_id="d1",
            document_name="Document",
            document_type="legal",
            domain="common",
            retrieval_score=1,
            content="Evidence",
        )
        return RAGSearchResult(
            success=True,
            original_query=request.query,
            normalized_query=request.query,
            context="[SOURCE_1] Evidence",
            sources=[source],
        )


def test_rag_tool_and_future_contract_boundaries() -> None:
    context = AgentExecutionContext(request_id="r")
    result = RAGSearchTool(StubRAG()).execute(RAGSearchTool.input_model(query="law"), context)
    assert result.source_ids == ["SOURCE_1"]
    assert "answer" not in result.data
    assert fake_data_query_tool({"count": 10}).execute(Input(value=1), context).data[
        "official_operational_data"
    ] == {"count": 10}
    assert "deterministic_kpis" in fake_kpi_tool({}).execute(Input(value=1), context).data
    rules = fake_rule_engine_tool(["review"]).execute(Input(value=1), context).data
    assert rules["official_data_modified"] is False
    assert fake_report_export_tool().execute(Input(value=1), context).data["exported"] is False
