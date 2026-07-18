"""Opt-in fake-provider Agent endpoint for an offline, bounded MVP workflow."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.models import AgentRequest
from app.agent.orchestrator import AgentOrchestrator
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.operational_tools import (
    DeterministicKPITool,
    OperationalDataQueryTool,
    StoredValidationTool,
)
from app.database import get_session
from app.llm.fake import FakeLLMClient
from app.llm.models import LLMResponse, ToolCall
from app.models.operational_report import OperationalReportRecord

router = APIRouter(prefix="/agent", tags=["agent"])


class OfflineAgentRequest(BaseModel):
    report_id: str = Field(min_length=1)
    user_request: str = Field(min_length=1)


@router.post("/analyze")
def analyze_with_fake_provider(
    request: OfflineAgentRequest,
    session: Annotated[Session, Depends(get_session)],
):
    record = session.get(OperationalReportRecord, request.report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Operational report not found")
    registry = ToolRegistry()
    registry.register(OperationalDataQueryTool(session))
    registry.register(DeterministicKPITool(session))
    registry.register(StoredValidationTool(session))
    arguments = {"report_id": request.report_id}
    responses = [
        LLMResponse(tool_calls=[ToolCall(id="data", name="data_query", arguments=arguments)]),
        LLMResponse(tool_calls=[ToolCall(id="kpi", name="kpi", arguments=arguments)]),
        LLMResponse(tool_calls=[ToolCall(id="rules", name="rule_engine", arguments=arguments)]),
        LLMResponse(
            content=json.dumps(
                {
                    "content": (
                        "Đã tổng hợp dữ liệu và kiểm tra bằng provider giả lập; cần cán bộ duyệt."
                    ),
                    "human_review_required": True,
                    "warnings": [
                        "Không gọi FPT API.",
                        "Không sử dụng Ground Truth.",
                        "Quy tắc và KPI chỉ dành cho dữ liệu thử nghiệm tổng hợp.",
                    ],
                },
                ensure_ascii=False,
            )
        ),
    ]
    result = AgentOrchestrator(
        FakeLLMClient(responses), registry, allow_scaffold_run=True, max_steps=6
    ).run(AgentRequest(user_request=request.user_request))
    return result.model_dump(mode="json")
