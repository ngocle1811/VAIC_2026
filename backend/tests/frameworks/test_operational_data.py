from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.operational_data.models import (
    IssueSeverity,
    OperationalProcessingStatus,
    OperationalValidationResult,
    ReportingPeriod,
    ValidationIssue,
)
from app.operational_data.service import OperationalDataService


class Validator:
    def __init__(self, warning: bool = False, mutate: bool = False) -> None:
        self.warning = warning
        self.mutate = mutate

    def validate(self, report):
        if self.mutate:
            report.values["metric_alpha"] = 999
        warnings = (
            [
                ValidationIssue(
                    code="synthetic_warning",
                    message="Synthetic warning",
                    severity=IssueSeverity.WARNING,
                )
            ]
            if self.warning
            else []
        )
        return OperationalValidationResult(report=report, warnings=warnings)


def test_reporting_period_and_provenance_validation() -> None:
    with pytest.raises(ValidationError):
        ReportingPeriod(kind="custom", start="2099-02-01", end="2099-01-01")


def test_operational_service_preserves_values_and_sets_review_status(synthetic_report) -> None:
    before = deepcopy(synthetic_report.values)
    result = OperationalDataService(Validator(warning=True)).validate(synthetic_report)
    assert result.values == before
    assert result.processing_status == OperationalProcessingStatus.NEEDS_REVIEW
    with pytest.raises(ValueError, match="must not modify"):
        OperationalDataService(Validator(mutate=True)).validate(synthetic_report)
