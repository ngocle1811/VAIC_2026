"""Orchestrate generic validation without changing extracted source values."""

from copy import deepcopy

from app.operational_data.interfaces import OperationalReportRepository, OperationalReportValidator
from app.operational_data.models import OperationalProcessingStatus, OperationalReport


class OperationalDataService:
    def __init__(
        self,
        validator: OperationalReportValidator,
        repository: OperationalReportRepository | None = None,
    ) -> None:
        self.validator = validator
        self.repository = repository

    def validate(self, report: OperationalReport) -> OperationalReport:
        original_values = deepcopy(report.values)
        result = self.validator.validate(report.model_copy(deep=True))
        if result.report.values != original_values:
            raise ValueError("validator must not modify operational source values")
        status = (
            OperationalProcessingStatus.FAILED
            if result.errors
            else (
                OperationalProcessingStatus.NEEDS_REVIEW
                if result.warnings
                else OperationalProcessingStatus.VALIDATED
            )
        )
        validated = result.report.model_copy(
            update={"processing_status": status, "issues": result.errors + result.warnings}
        )
        return self.repository.save(validated) if self.repository else validated
