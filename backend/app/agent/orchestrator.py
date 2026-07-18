"""Bounded explicit Agent scaffold; production execution is disabled by default."""

import json
from uuid import uuid4

from app.agent.models import (
    AgentExecutionContext,
    AgentRequest,
    AgentResponse,
    AgentState,
    AgentStep,
    AgentWarning,
)
from app.agent.prompt_loader import load_prompt
from app.agent.tool_registry import ToolRegistry
from app.llm.base import LLMClient
from app.llm.models import LLMMessage, LLMRequest, StructuredLLMResult
from app.rag.citations.validator import CitationValidator
from app.rag.retrieval.models import BuiltContext, CitationReference, ContextSource


class AgentOrchestrator:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        *,
        max_steps: int = 6,
        production_enabled: bool = False,
        allow_scaffold_run: bool = False,
        max_tool_errors: int = 2,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps
        self.production_enabled = production_enabled
        self.allow_scaffold_run = allow_scaffold_run
        self.max_tool_errors = max_tool_errors

    def run(self, request: AgentRequest) -> AgentResponse:
        if not self.production_enabled and not self.allow_scaffold_run:
            state = AgentState(original_user_request=request.user_request)
            state.warnings.append(
                AgentWarning(
                    code="production_disabled",
                    message="Production Agent orchestration is disabled.",
                )
            )
            return AgentResponse(success=False, state=state)
        state = AgentState(original_user_request=request.user_request)
        context = AgentExecutionContext(request_id=str(uuid4()))
        messages = [
            LLMMessage(role="system", content=load_prompt("agent_system.txt")),
            LLMMessage(role="user", content=request.user_request),
        ]
        seen_signatures: set[str] = set()
        error_count = 0
        for step_number in range(1, self.max_steps + 1):
            response = self.llm.generate(
                LLMRequest(
                    messages=messages,
                    tools=[
                        {
                            "type": "function",
                            "function": {
                                "name": definition.name,
                                "description": definition.description,
                                "parameters": definition.input_schema,
                            },
                        }
                        for definition in self.registry.definitions()
                    ],
                )
            )
            if not response.tool_calls:
                result = self._finalize(response.content or "", state)
                return AgentResponse(
                    success=not result.human_review_required, result=result, state=state
                )
            for call in response.tool_calls:
                signature = f"{call.name}:{json.dumps(call.arguments, sort_keys=True)}"
                if signature in seen_signatures:
                    state.warnings.append(
                        AgentWarning(
                            code="repeated_tool_call", message="Repeated tool call stopped."
                        )
                    )
                    return AgentResponse(success=False, state=state)
                seen_signatures.add(signature)
                tool_result = self.registry.execute(call.name, call.arguments, context)
                state.tool_execution_history.append(
                    AgentStep(
                        step_number=step_number,
                        tool_name=call.name,
                        arguments=call.arguments,
                        success=tool_result.success,
                        summary=(
                            tool_result.error.message if tool_result.error else "Tool completed"
                        ),
                    )
                )
                if not tool_result.success:
                    error_count += 1
                    if error_count >= self.max_tool_errors:
                        state.warnings.append(
                            AgentWarning(
                                code="tool_error_limit", message="Tool error limit reached."
                            )
                        )
                        return AgentResponse(success=False, state=state)
                self._apply_tool_result(call.name, tool_result.data, state)
                messages.append(
                    LLMMessage(
                        role="tool",
                        tool_call_id=call.id,
                        name=call.name,
                        content=json.dumps(tool_result.model_dump(mode="json"), ensure_ascii=False),
                    )
                )
        state.warnings.append(
            AgentWarning(code="maximum_steps", message="Maximum Agent steps reached.")
        )
        return AgentResponse(success=False, state=state)

    @staticmethod
    def _apply_tool_result(name: str, data: dict, state: AgentState) -> None:
        if name == "rag_search":
            state.rag_context = str(data.get("context", ""))
            sources = data.get("sources", [])
            state.rag_sources = sources if isinstance(sources, list) else []
        elif name == "data_query":
            official = data.get("official_operational_data", {})
            if isinstance(official, dict):
                if state.operational_data and state.operational_data != official:
                    state.warnings.append(
                        AgentWarning(
                            code="official_data_overwrite_rejected",
                            message=(
                                "A tool attempted to replace previously recorded official data."
                            ),
                        )
                    )
                    state.human_review_required = True
                else:
                    state.operational_data = official
        elif name == "kpi":
            result = data.get("deterministic_kpis", {})
            if isinstance(result, dict):
                state.kpi_results = result
        elif name == "rule_engine":
            state.rule_validation_results = data

    @staticmethod
    def _finalize(content: str, state: AgentState) -> StructuredLLMResult:
        try:
            result = StructuredLLMResult.model_validate_json(content)
        except Exception:
            result = StructuredLLMResult(content=content)
        sources = [ContextSource.model_validate(source) for source in state.rag_sources]
        rag_context = state.rag_context or ""
        validation = CitationValidator().validate(
            [CitationReference(source_id=source_id) for source_id in result.used_source_ids],
            BuiltContext(
                text=rag_context,
                sources=sources,
                estimated_tokens=max(0, len(rag_context) // 4),
            ),
        )
        if not validation.valid:
            result.warnings.append("Unsupported source identifiers were rejected.")
            invalid = {item.citation.source_id for item in validation.rejected}
            result.used_source_ids = [
                item for item in result.used_source_ids if item not in invalid
            ]
            result.human_review_required = True
            state.human_review_required = True
        state.final_response = result.content
        return result
