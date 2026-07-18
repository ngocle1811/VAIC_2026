"""Generic operational report models without invented domain fields."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class OperationalDomain(StrEnum):
    POPULATION = "population"
    COMPLAINTS = "complaints"
    TASKS = "tasks"


class DataClassification(StrEnum):
    OFFICIAL_CANDIDATE = "official_candidate"
    SYNTHETIC_TEST_DATA = "SYNTHETIC_TEST_DATA"


class OperationalProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class ReportingPeriodKind(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


OperationalScalar = str | int | Decimal | bool | date | None


class ReportingPeriod(BaseModel):
    kind: ReportingPeriodKind
    start: date
    end: date
    label: str | None = None

    @model_validator(mode="after")
    def validate_order(self) -> ReportingPeriod:
        if self.end < self.start:
            raise ValueError("reporting period end must not precede start")
        return self


class OrganizationMetadata(BaseModel):
    organization_id: str = Field(min_length=1, max_length=128)
    organization_name: str = Field(min_length=1, max_length=512)
    parent_organization_id: str | None = Field(default=None, max_length=128)
    department_id: str | None = Field(default=None, max_length=128)


class CommonReportMetadata(BaseModel):
    report_id: str = Field(min_length=1, max_length=128)
    domain: OperationalDomain
    reporting_period: ReportingPeriod
    organization: OrganizationMetadata
    classification: DataClassification
    received_at: datetime | None = None
    schema_version: str | None = None


class SourceProvenance(BaseModel):
    source_file_id: str = Field(min_length=1, max_length=256)
    source_sha256: Annotated[str | None, Field(pattern=r"^[a-fA-F0-9]{64}$")] = None
    page_number: int | None = Field(default=None, ge=1)
    sheet_name: str | None = Field(default=None, max_length=256)
    row_number: int | None = Field(default=None, ge=1)
    cell_range: str | None = Field(default=None, max_length=64)
    extraction_method: str = Field(min_length=1, max_length=128)
    model_produced: bool = False
    evidence: str | None = Field(default=None, max_length=2000)


class ValidationIssue(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=1000)
    severity: IssueSeverity
    field_path: str | None = Field(default=None, max_length=512)
    source: SourceProvenance | None = None


class OperationalReport(BaseModel):
    metadata: CommonReportMetadata
    values: dict[str, OperationalScalar] = Field(default_factory=dict)
    provenance: dict[str, list[SourceProvenance]] = Field(default_factory=dict)
    records: list[dict[str, OperationalScalar]] = Field(default_factory=list)
    processing_status: OperationalProcessingStatus = OperationalProcessingStatus.EXTRACTED
    issues: list[ValidationIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provenance_keys(self) -> OperationalReport:
        unknown = set(self.provenance) - set(self.values)
        if unknown:
            raise ValueError(f"provenance references unknown fields: {sorted(unknown)}")
        return self


class OperationalUploadResult(BaseModel):
    """API-safe result of a deterministic operational upload."""

    report: OperationalReport
    duplicate: bool = False
    source_path_preserved: bool = True


class OperationalValidationResult(BaseModel):
    report: OperationalReport
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors
