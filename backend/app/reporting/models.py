from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from app.operational_data.models import OperationalDomain


class ReportStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class ReportRequest(BaseModel):
    report_id: str = Field(min_length=1)
    domain: OperationalDomain
    operational_report_id: str = Field(min_length=1)
    template_id: str = Field(min_length=1)
    allowed_source_ids: list[str] = Field(default_factory=list)
    human_review_required: bool = True


class ReportCitation(BaseModel):
    source_id: str = Field(min_length=1)
    chunk_id: str | None = None
    document_id: str | None = None


class NumericSourceReference(BaseModel):
    field_name: str = Field(min_length=1)
    value: Decimal


class ReportSection(BaseModel):
    heading: str = Field(min_length=1)
    content: str = ""
    citations: list[ReportCitation] = Field(default_factory=list)
    numeric_sources: list[NumericSourceReference] = Field(default_factory=list)


class ReportTable(BaseModel):
    title: str | None = None
    headers: list[str] = Field(min_length=1)
    rows: list[list[str]] = Field(default_factory=list)
    numeric_sources: list[NumericSourceReference] = Field(default_factory=list)


class ReportDraft(BaseModel):
    request: ReportRequest
    title: str = Field(min_length=1)
    reporting_period_label: str
    sections: list[ReportSection] = Field(default_factory=list)
    tables: list[ReportTable] = Field(default_factory=list)
    status: ReportStatus = ReportStatus.DRAFT
    warnings: list[str] = Field(default_factory=list)


class ReportValidationIssue(BaseModel):
    code: str
    message: str
    location: str | None = None


class ReportValidationResult(BaseModel):
    valid: bool
    issues: list[ReportValidationIssue] = Field(default_factory=list)
