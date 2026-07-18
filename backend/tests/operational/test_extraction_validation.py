from pathlib import Path

import pytest

from app.operational_data.extraction import RepositoryOperationalExtractor
from app.operational_data.models import DataClassification, OperationalDomain
from app.operational_data.validation import SyntheticOperationalValidator


DATASET = Path(__file__).parents[3] / "ubnd_report_dataset" / "01_input_reports"


@pytest.mark.parametrize(
    ("domain", "relative", "expected_value", "expected_records"),
    [
        (
            OperationalDomain.POPULATION,
            "population/normal/bao_cao_dan_cu_thang_04_2026.xlsx",
            18505,
            0,
        ),
        (
            OperationalDomain.POPULATION,
            "population/normal/bao_cao_dan_cu_thang_05_2026.docx",
            18557,
            0,
        ),
        (
            OperationalDomain.POPULATION,
            "population/normal/bao_cao_dan_cu_thang_06_2026.pdf",
            18621,
            0,
        ),
        (
            OperationalDomain.COMPLAINTS,
            "complaints/normal/bao_cao_khieu_nai_to_cao_thang_06_2026.pdf",
            45,
            0,
        ),
        (
            OperationalDomain.TASKS,
            "tasks/normal/bao_cao_tien_do_nhiem_vu_thang_06_2026.xlsx",
            18,
            18,
        ),
    ],
)
def test_repository_synthetic_formats(domain, relative, expected_value, expected_records):
    report = RepositoryOperationalExtractor().extract(DATASET / relative, domain)
    assert report.metadata.classification is DataClassification.SYNTHETIC_TEST_DATA
    field = {
        OperationalDomain.POPULATION: "population_total",
        OperationalDomain.COMPLAINTS: "received_cases",
        OperationalDomain.TASKS: "task_total",
    }[domain]
    assert report.values[field] == expected_value
    assert len(report.records) == expected_records
    assert all(
        source.model_produced is False
        for sources in report.provenance.values()
        for source in sources
    )


def test_invalid_fixture_errors_are_deterministic_and_values_unchanged():
    path = DATASET / "complaints/invalid/bao_cao_khieu_nai_to_cao_thang_06_2026_sai_tong.xlsx"
    report = RepositoryOperationalExtractor().extract(path, OperationalDomain.COMPLAINTS)
    before = report.model_dump(mode="json")["values"]
    result = SyntheticOperationalValidator().validate(report)
    assert {issue.code for issue in result.errors} == {
        "COM_TYPE_TOTAL_MISMATCH",
        "COM_AUTHORITY_TOTAL_MISMATCH",
    }
    assert result.report.model_dump(mode="json")["values"] == before


def test_invalid_tasks_detect_safe_draft_rules():
    path = DATASET / "tasks/invalid/bao_cao_tien_do_nhiem_vu_thang_06_2026_du_lieu_loi.xlsx"
    report = RepositoryOperationalExtractor().extract(path, OperationalDomain.TASKS)
    result = SyntheticOperationalValidator().validate(report)
    assert {issue.code for issue in result.errors} >= {
        "TASK_LEAD_UNIT_REQUIRED",
        "TASK_PROGRESS_RANGE",
        "TASK_COMPLETION_BEFORE_ASSIGNMENT",
    }
    assert "TASK_OVERDUE_STATUS" in {issue.code for issue in result.warnings}
