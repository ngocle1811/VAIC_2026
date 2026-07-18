"""Conservative deterministic tool hints; tools remain the Agent's explicit choice."""

import re

from pydantic import BaseModel, Field


class AgentDecision(BaseModel):
    suggested_tools: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class AgentDecisionRules:
    """Suggest capability classes without defining official business rules."""

    _patterns = (
        (
            "rag_search",
            re.compile(
                r"\b(?:regulation|citation|source|legal|template|quy định|trích dẫn|nguồn|"
                r"pháp lý|biểu mẫu)\b",
                re.I,
            ),
        ),
        (
            "data_query",
            re.compile(
                r"\b(?:current|official|count|total|records?|hiện tại|số liệu|tổng|bản ghi)\b", re.I
            ),
        ),
        ("kpi", re.compile(r"\b(?:kpi|ratio|rate|percentage|tỷ lệ|chỉ số)\b", re.I)),
        (
            "rule_engine",
            re.compile(r"\b(?:validate|check|warning|error|kiểm tra|cảnh báo|lỗi)\b", re.I),
        ),
        (
            "report_export",
            re.compile(r"\b(?:draft|report|export|docx|báo cáo|xuất|bản nháp)\b", re.I),
        ),
    )

    def analyze(self, request: str) -> AgentDecision:
        tools = []
        reasons = []
        for tool, pattern in self._patterns:
            if pattern.search(request):
                tools.append(tool)
                reasons.append(f"Request contains a generic {tool} capability signal.")
        return AgentDecision(suggested_tools=tools, reasons=reasons)
