"""Persistent operational-report and generated-report lifecycle records."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OperationalReportRecord(Base):
    __tablename__ = "operational_reports"
    __table_args__ = (
        Index("ix_operational_reports_domain", "domain"),
        Index("ix_operational_reports_period", "period_start", "period_end"),
        Index("ix_operational_reports_checksum", "checksum_sha256"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain: Mapped[str] = mapped_column(String(32), nullable=False)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False)
    period_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    period_start: Mapped[str] = mapped_column(String(10), nullable=False)
    period_end: Mapped[str] = mapped_column(String(10), nullable=False)
    period_label: Mapped[str | None] = mapped_column(String(255))
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    organization_name: Mapped[str] = mapped_column(String(512), nullable=False)
    values: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    records: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    issues: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GeneratedReportRecord(Base):
    __tablename__ = "generated_reports"
    __table_args__ = (Index("ix_generated_reports_status", "status"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operational_report_id: Mapped[str] = mapped_column(
        ForeignKey("operational_reports.id"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(32), nullable=False)
    template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="needs_review")
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    validation_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reviewer_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
