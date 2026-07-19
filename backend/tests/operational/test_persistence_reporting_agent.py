from pathlib import Path

from docx import Document

from app.agent.models import AgentExecutionContext
from app.agent.tools.operational_tools import (
    DeterministicKPITool,
    OperationalDataQueryTool,
    ReportLookupRequest,
    StoredValidationTool,
)
from app.models.operational_report import OperationalReportRecord
from app.operational_data.models import OperationalDomain
from app.operational_data.pipeline import OperationalPipelineService
from app.operational_data.repository import SqlOperationalReportRepository
from app.reporting.models import ReportStatus
from app.reporting.repository import GeneratedReportRepository
from app.reporting.service import ReportGenerationService

DATASET = Path(__file__).parents[3] / "ubnd_report_dataset" / "01_input_reports"


def test_persistence_idempotency_tools_report_and_review(db_session, tmp_path):
    source = DATASET / "population/normal/bao_cao_dan_cu_thang_04_2026.xlsx"
    repository = SqlOperationalReportRepository(db_session)
    pipeline = OperationalPipelineService(repository, tmp_path / "operational", 10)
    record, duplicate = pipeline.ingest(source, source.name, OperationalDomain.POPULATION)
    repeated, duplicate_repeated = pipeline.ingest(
        source, source.name, OperationalDomain.POPULATION
    )
    assert not duplicate
    assert duplicate_repeated and repeated.id == record.id
    assert db_session.query(OperationalReportRecord).count() == 1
    assert Path(record.file_path).is_file()

    arguments = ReportLookupRequest(report_id=record.id)
    context = AgentExecutionContext(request_id="test")
    data = OperationalDataQueryTool(db_session).execute(arguments, context)
    kpis = DeterministicKPITool(db_session).execute(arguments, context)
    rules = StoredValidationTool(db_session).execute(arguments, context)
    assert data.data["official_operational_data"]["values"]["population_total"] == 18505
    assert "population_net_change" in kpis.data["deterministic_kpis"]
    assert rules.data["official_data_modified"] is False

    report_repository = GeneratedReportRepository(db_session)
    generated = ReportGenerationService(report_repository, tmp_path / "reports").generate(
        record, "synthetic_domain_draft"
    )
    assert generated.status == ReportStatus.NEEDS_REVIEW.value
    document = Document(generated.artifact_path)
    assert "SYNTHETIC_TEST_DATA" in "\n".join(item.text for item in document.paragraphs)
    approved = report_repository.review(
        generated, ReportStatus.APPROVED, "reviewer-test", "Synthetic fixture reviewed"
    )
    assert approved.status == ReportStatus.APPROVED.value
