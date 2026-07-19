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


class PopulationSourceRole(StrEnum):
    """Deterministic role of one workbook in a population bundle."""

    OPENING_BALANCE = "OPENING_BALANCE"
    CIVIL_STATUS = "CIVIL_STATUS"
    RESIDENCE_MOVEMENT = "RESIDENCE_MOVEMENT"


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
    source_role: PopulationSourceRole | None = None


class ValidationIssue(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=1000)
    severity: IssueSeverity
    field_path: str | None = Field(default=None, max_length=512)
    source: SourceProvenance | None = None


class PopulationReportValues(BaseModel):
    """Canonical population values; missing source values remain null."""

    population_opening: int | None = Field(default=None, ge=0)
    population_closing: int | None = Field(default=None, ge=0)
    birth_registered: int | None = Field(default=None, ge=0)
    birth_local_resident: int | None = Field(default=None, ge=0)
    death_registered: int | None = Field(default=None, ge=0)
    death_local_resident: int | None = Field(default=None, ge=0)
    permanent_in: int | None = Field(default=None, ge=0)
    permanent_out: int | None = Field(default=None, ge=0)
    temporary_opening: int | None = Field(default=None, ge=0)
    temporary_new: int | None = Field(default=None, ge=0)
    temporary_removed: int | None = Field(default=None, ge=0)
    temporary_closing: int | None = Field(default=None, ge=0)


class PopulationExtractedSource(BaseModel):
    """One population workbook after deterministic extraction and reconciliation."""

    role: PopulationSourceRole
    source_filename: str = Field(min_length=1, max_length=512)
    source_sha256: Annotated[str, Field(pattern=r"^[a-fA-F0-9]{64}$")]
    reporting_period: ReportingPeriod
    organization: OrganizationMetadata
    classification: DataClassification
    values: dict[str, int] = Field(default_factory=dict)
    provenance: dict[str, list[SourceProvenance]] = Field(default_factory=dict)
    sheet_names: list[str] = Field(default_factory=list)
    detail_counts: dict[str, int] = Field(default_factory=dict)
    detail_record_count: int = Field(default=0, ge=0)
    extraction_warnings: list[ValidationIssue] = Field(default_factory=list)


class PopulationSourceBundle(BaseModel):
    """Unstandardized population inputs; role completeness is checked by the standardizer."""

    sources: list[PopulationExtractedSource] = Field(min_length=1)


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
