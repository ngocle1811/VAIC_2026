"""Operational upload, extraction, validation, preservation, and persistence."""

import hashlib
import shutil
from pathlib import Path

from app.operational_data.extraction import RepositoryOperationalExtractor
from app.operational_data.models import OperationalDomain
from app.operational_data.repository import SqlOperationalReportRepository
from app.operational_data.service import OperationalDataService
from app.operational_data.validation import SyntheticOperationalValidator
from app.security.file_validation import validate_operational_file


class OperationalPipelineService:
    def __init__(self, repository: SqlOperationalReportRepository, storage_dir: Path, max_mb: int):
        self.repository = repository
        self.storage_dir = storage_dir
        self.max_bytes = max_mb * 1024 * 1024
        self.extractor = RepositoryOperationalExtractor()

    def ingest(self, source_path: Path, original_filename: str, domain: OperationalDomain):
        validate_operational_file(source_path, self.max_bytes)
        checksum = hashlib.sha256(source_path.read_bytes()).hexdigest()
        existing = self.repository.get_by_checksum(checksum, domain)
        if existing:
            return existing, True
        target_dir = self.storage_dir / domain.value / checksum[:2]
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{checksum}_{Path(original_filename).name}"
        target = target_dir / safe_name
        shutil.copy2(source_path, target)
        try:
            extracted = self.extractor.extract(target, domain)
            validated = OperationalDataService(SyntheticOperationalValidator()).validate(extracted)
            record = self.repository.save(
                validated, filename=original_filename, file_path=str(target), checksum=checksum
            )
            return record, False
        except Exception:
            target.unlink(missing_ok=True)
            raise

    def get(self, report_id: str):
        return self.repository.get(report_id)

    def list(self, domain: OperationalDomain | None = None):
        return self.repository.list(domain)


def record_payload(record) -> dict:
    return {
        "report_id": record.id,
        "domain": record.domain,
        "classification": record.classification,
        "original_filename": record.original_filename,
        "processing_status": record.processing_status,
        "reporting_period": {
            "kind": record.period_kind,
            "start": record.period_start,
            "end": record.period_end,
            "label": record.period_label,
        },
        "organization": {
            "organization_id": record.organization_id,
            "organization_name": record.organization_name,
        },
        "values": record.values,
        "records": record.records,
        "provenance": record.provenance,
        "issues": record.issues,
        "created_at": record.created_at,
    }
