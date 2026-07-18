import json

from app.agent.decision_rules import AgentDecisionRules
from app.agent.factory import create_agent_orchestrator
from app.agent.models import AgentRequest
from app.agent.orchestrator import AgentOrchestrator
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.future_contracts import fake_data_query_tool
from app.agent.tools.rag_search_tool import RAGSearchTool
from app.config import Settings
from app.llm.fake import FakeLLMClient
from app.llm.models import LLMResponse, ToolCall
from tests.phase4.test_llm_registry_tools import StubRAG


def _call(arguments=None, name="rag_search") -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id="call-1", name=name, arguments=arguments or {"query": "law"})]
    )


def test_orchestrator_rag_flow_preserves_sources_and_state_boundaries() -> None:
    registry = ToolRegistry()
    registry.register(RAGSearchTool(StubRAG()))
    final = json.dumps({"content": "Evidence response", "used_source_ids": ["SOURCE_1"]})
    llm = FakeLLMClient([_call(), LLMResponse(content=final)])
    result = AgentOrchestrator(llm, registry, allow_scaffold_run=True, max_steps=3).run(
        AgentRequest(user_request="Find regulation")
    )
    assert result.success
    assert result.result.used_source_ids == ["SOURCE_1"]
    assert result.state.rag_context == "[SOURCE_1] Evidence"
    assert result.state.operational_data == {}
    assert len(result.state.tool_execution_history) == 1


def test_production_disabled_repeated_unknown_and_max_steps() -> None:
    registry = ToolRegistry()
    registry.register(RAGSearchTool(StubRAG()))
    disabled = AgentOrchestrator(FakeLLMClient([]), registry).run(
        AgentRequest(user_request="request")
    )
    assert not disabled.success and disabled.state.warnings[0].code == "production_disabled"

    repeated = AgentOrchestrator(
        FakeLLMClient([_call(), _call()]),
        registry,
        allow_scaffold_run=True,
        max_steps=3,
    ).run(AgentRequest(user_request="request"))
    assert not repeated.success
    assert repeated.state.warnings[-1].code == "repeated_tool_call"

    unknown = AgentOrchestrator(
        FakeLLMClient([_call(name="unknown")]),
        registry,
        allow_scaffold_run=True,
        max_tool_errors=1,
    ).run(AgentRequest(user_request="request"))
    assert unknown.state.warnings[-1].code == "tool_error_limit"

    maximum = AgentOrchestrator(
        FakeLLMClient([_call({"query": "one"}), _call({"query": "two"})]),
        registry,
        allow_scaffold_run=True,
        max_steps=2,
    ).run(AgentRequest(user_request="request"))
    assert maximum.state.warnings[-1].code == "maximum_steps"


def test_invalid_source_id_requires_human_review() -> None:
    registry = ToolRegistry()
    registry.register(RAGSearchTool(StubRAG()))
    final = json.dumps({"content": "Unsupported", "used_source_ids": ["SOURCE_99"]})
    result = AgentOrchestrator(
        FakeLLMClient([_call(), LLMResponse(content=final)]),
        registry,
        allow_scaffold_run=True,
    ).run(AgentRequest(user_request="request"))
    assert result.result.human_review_required
    assert result.result.used_source_ids == []
    assert result.state.human_review_required


def test_official_data_overwrite_is_rejected() -> None:
    registry = ToolRegistry()
    registry.register(fake_data_query_tool({"metric_alpha": 1}))
    first = LLMResponse(
        tool_calls=[ToolCall(id="one", name="data_query", arguments={"fields": ["metric_alpha"]})]
    )
    orchestrator = AgentOrchestrator(
        FakeLLMClient([first, LLMResponse(content='{"content":"done"}')]),
        registry,
        allow_scaffold_run=True,
    )
    result = orchestrator.run(AgentRequest(user_request="request"))
    assert result.state.operational_data == {"metric_alpha": 1}
    AgentOrchestrator._apply_tool_result(
        "data_query",
        {"official_operational_data": {"metric_alpha": 2}},
        result.state,
    )
    assert result.state.operational_data == {"metric_alpha": 1}
    assert result.state.warnings[-1].code == "official_data_overwrite_rejected"


def test_agent_decision_hints_and_factory_are_deterministic() -> None:
    decision = AgentDecisionRules().analyze("validate report citation and total")
    assert decision.suggested_tools == [
        "rag_search",
        "data_query",
        "rule_engine",
        "report_export",
    ]
    settings = Settings(_env_file=None, llm_provider="fake")
    orchestrator = create_agent_orchestrator(
        settings,
        FakeLLMClient([LLMResponse(content='{"content":"ok"}')]),
        [],
        allow_scaffold_run=True,
    )
    assert orchestrator.run(AgentRequest(user_request="request")).success
