"""Typed fake operational tools documenting future source-of-truth boundaries."""

from typing import Any

from pydantic import BaseModel

from app.agent.models import AgentExecutionContext, ToolResult


class DataQueryRequest(BaseModel):
    fields: list[str]


class KPIRequest(BaseModel):
    metric_names: list[str]
    operational_data: dict[str, Any]


class RuleEngineRequest(BaseModel):
    operational_data: dict[str, Any]


class ReportExportRequest(BaseModel):
    validated_report: dict[str, Any]


class _FakeTool:
    description = "Phase 4 scaffold fake; no production business logic."

    def __init__(self, name: str, input_model: type[BaseModel], result: dict[str, Any]) -> None:
        self.name = name
        self.input_model = input_model
        self.result = result

    def execute(self, arguments: BaseModel, context: AgentExecutionContext) -> ToolResult:
        return ToolResult(success=True, data=dict(self.result))


def fake_data_query_tool(data: dict[str, Any]) -> _FakeTool:
    return _FakeTool("data_query", DataQueryRequest, {"official_operational_data": data})


def fake_kpi_tool(data: dict[str, Any]) -> _FakeTool:
    return _FakeTool("kpi", KPIRequest, {"deterministic_kpis": data})


def fake_rule_engine_tool(warnings: list[str]) -> _FakeTool:
    return _FakeTool(
        "rule_engine",
        RuleEngineRequest,
        {"validation_warnings": warnings, "official_data_modified": False},
    )


def fake_report_export_tool() -> _FakeTool:
    return _FakeTool(
        "report_export",
        ReportExportRequest,
        {"exported": False, "reason": "scaffold_only"},
    )
