"""Agent tools backed by PostgreSQL operational data and deterministic engines."""

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.models import AgentExecutionContext, ToolResult
from app.kpi.catalog import calculate_fixture_kpis
from app.models.operational_report import OperationalReportRecord


class ReportLookupRequest(BaseModel):
    report_id: str = Field(min_length=1)


class OperationalDataQueryTool:
    name = "data_query"
    description = "Read standardized operational data from PostgreSQL by report ID."
    input_model = ReportLookupRequest

    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(self, arguments: ReportLookupRequest, context: AgentExecutionContext) -> ToolResult:
        record = self.session.get(OperationalReportRecord, arguments.report_id)
        if not record:
            return ToolResult(success=False, data={}, source_ids=[])
        return ToolResult(
            success=True,
            data={
                "official_operational_data": {
                    "report_id": record.id,
                    "domain": record.domain,
                    "classification": record.classification,
                    "values": record.values,
                    "records": record.records,
                }
            },
            source_ids=[record.id],
        )


class DeterministicKPITool:
    name = "kpi"
    description = "Calculate whitelisted deterministic KPIs from one operational report."
    input_model = ReportLookupRequest

    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(self, arguments: ReportLookupRequest, context: AgentExecutionContext) -> ToolResult:
        record = self.session.get(OperationalReportRecord, arguments.report_id)
        if not record:
            return ToolResult(success=False)
        from app.operational_data.models import OperationalDomain

        kpis = calculate_fixture_kpis(
            OperationalDomain(record.domain), record.classification, record.values
        )
        return ToolResult(
            success=True,
            data={"deterministic_kpis": {key: str(value) for key, value in kpis.items()}},
            source_ids=[record.id],
        )


class StoredValidationTool:
    name = "rule_engine"
    description = "Read deterministic validation results without changing source values."
    input_model = ReportLookupRequest

    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(self, arguments: ReportLookupRequest, context: AgentExecutionContext) -> ToolResult:
        record = self.session.get(OperationalReportRecord, arguments.report_id)
        if not record:
            return ToolResult(success=False)
        return ToolResult(
            success=True,
            data={
                "validation_issues": record.issues,
                "official_data_modified": False,
                "ruleset": "SYNTHETIC_NON_PRODUCTION_RULE",
            },
            source_ids=[record.id],
        )
