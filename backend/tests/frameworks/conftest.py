import json
from pathlib import Path

import pytest

from app.operational_data.models import (
    CommonReportMetadata,
    DataClassification,
    OperationalDomain,
    OperationalReport,
    OrganizationMetadata,
    ReportingPeriod,
)


@pytest.fixture
def synthetic_report() -> OperationalReport:
    return OperationalReport(
        metadata=CommonReportMetadata(
            report_id="synthetic-report",
            domain=OperationalDomain.TASKS,
            reporting_period=ReportingPeriod(kind="week", start="2099-01-05", end="2099-01-11"),
            organization=OrganizationMetadata(
                organization_id="synthetic-org",
                organization_name="SYNTHETIC ORGANIZATION",
            ),
            classification=DataClassification.SYNTHETIC_TEST_DATA,
        ),
        values={"metric_alpha": 20, "metric_beta": 15},
    )


def load_synthetic_pair(domain: str) -> tuple[dict, dict]:
    root = Path(__file__).parents[3] / "dataset" / "synthetic_tests"
    input_data = json.loads((root / "inputs" / f"{domain}.json").read_text(encoding="utf-8"))
    ground_truth = json.loads(
        (root / "ground_truth" / f"{domain}.json").read_text(encoding="utf-8")
    )
    return input_data, ground_truth
