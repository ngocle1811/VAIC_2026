"""Typed Agent scaffold models with explicit operational/evidence boundaries."""

from typing import Any

from pydantic import BaseModel, Field

from app.llm.models import StructuredLLMResult


class AgentRequest(BaseModel):
    user_request: str = Field(min_length=1)


class AgentWarning(BaseModel):
    code: str
    message: str


class AgentStep(BaseModel):
    step_number: int
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    summary: str = ""


class AgentExecutionContext(BaseModel):
    request_id: str
    operational_data: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class ToolError(BaseModel):
    code: str
    message: str


class ToolResult(BaseModel):
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: ToolError | None = None
    duration_ms: float = Field(default=0, ge=0)
    source_ids: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
    original_user_request: str
    task_classification: str | None = None
    operational_data: dict[str, Any] = Field(default_factory=dict)
    kpi_results: dict[str, Any] = Field(default_factory=dict)
    rule_validation_results: dict[str, Any] = Field(default_factory=dict)
    rag_context: str | None = None
    rag_sources: list[dict[str, Any]] = Field(default_factory=list)
    tool_execution_history: list[AgentStep] = Field(default_factory=list)
    warnings: list[AgentWarning] = Field(default_factory=list)
    draft_response: str | None = None
    final_response: str | None = None
    human_review_required: bool = False


class AgentResponse(BaseModel):
    success: bool
    result: StructuredLLMResult | None = None
    state: AgentState
