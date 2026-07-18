"""Replaceable extraction, validation, and persistence boundaries."""

from pathlib import Path
from typing import Literal, Protocol

from app.operational_data.models import (
    OperationalDomain,
    OperationalReport,
    OperationalValidationResult,
)


class OperationalReportExtractor(Protocol):
    domain: OperationalDomain

    def extract(self, source_path: Path) -> OperationalReport: ...


class PopulationReportExtractor(OperationalReportExtractor, Protocol):
    domain: Literal[OperationalDomain.POPULATION]


class ComplaintsReportExtractor(OperationalReportExtractor, Protocol):
    domain: Literal[OperationalDomain.COMPLAINTS]


class TasksReportExtractor(OperationalReportExtractor, Protocol):
    domain: Literal[OperationalDomain.TASKS]


class OperationalReportValidator(Protocol):
    def validate(self, report: OperationalReport) -> OperationalValidationResult: ...


class OperationalReportRepository(Protocol):
    def save(self, report: OperationalReport) -> OperationalReport: ...

    def get(self, report_id: str) -> OperationalReport | None: ...
