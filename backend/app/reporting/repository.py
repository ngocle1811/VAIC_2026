"""Generated-report persistence and explicit human-review transitions."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.operational_report import GeneratedReportRecord
from app.reporting.models import ReportStatus


class GeneratedReportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **values):
        record = GeneratedReportRecord(**values)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get(self, report_id: str):
        return self.session.get(GeneratedReportRecord, report_id)

    def list(self, status: ReportStatus | None = None):
        statement = select(GeneratedReportRecord).order_by(GeneratedReportRecord.created_at.desc())
        if status:
            statement = statement.where(GeneratedReportRecord.status == status.value)
        return list(self.session.scalars(statement))

    def review(self, record, status: ReportStatus, reviewer: str, comment: str | None):
        if status not in {ReportStatus.APPROVED, ReportStatus.REJECTED}:
            raise ValueError("review status must be approved or rejected")
        if record.status != ReportStatus.NEEDS_REVIEW.value:
            raise ValueError("only reports awaiting review can be reviewed")
        record.status = status.value
        record.reviewed_by = reviewer
        record.reviewer_comment = comment
        record.reviewed_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(record)
        return record
