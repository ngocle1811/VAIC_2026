"""SQLAlchemy persistence for standardized operational reports."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.operational_report import OperationalReportRecord
from app.operational_data.models import OperationalDomain, OperationalReport


class SqlOperationalReportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, report: OperationalReport, *, filename: str, file_path: str, checksum: str):
        record = self.session.get(OperationalReportRecord, report.metadata.report_id)
        payload = report.model_dump(mode="json")
        values = {
            "id": report.metadata.report_id,
            "domain": report.metadata.domain.value,
            "classification": report.metadata.classification.value,
            "original_filename": filename,
            "file_path": file_path,
            "checksum_sha256": checksum,
            "processing_status": report.processing_status.value,
            "period_kind": report.metadata.reporting_period.kind.value,
            "period_start": report.metadata.reporting_period.start.isoformat(),
            "period_end": report.metadata.reporting_period.end.isoformat(),
            "period_label": report.metadata.reporting_period.label,
            "organization_id": report.metadata.organization.organization_id,
            "organization_name": report.metadata.organization.organization_name,
            "values": payload["values"],
            "records": payload["records"],
            "provenance": payload["provenance"],
            "issues": payload["issues"],
        }
        if record is None:
            record = OperationalReportRecord(**values)
            self.session.add(record)
        else:
            for name, value in values.items():
                if name != "id":
                    setattr(record, name, value)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get(self, report_id: str):
        return self.session.get(OperationalReportRecord, report_id)

    def get_by_checksum(self, checksum: str, domain: OperationalDomain):
        return self.session.scalar(
            select(OperationalReportRecord).where(
                OperationalReportRecord.checksum_sha256 == checksum,
                OperationalReportRecord.domain == domain.value,
            )
        )

    def list(self, domain: OperationalDomain | None = None):
        statement = select(OperationalReportRecord).order_by(
            OperationalReportRecord.created_at.desc()
        )
        if domain:
            statement = statement.where(OperationalReportRecord.domain == domain.value)
        return list(self.session.scalars(statement))
