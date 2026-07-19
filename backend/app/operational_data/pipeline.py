"""Operational upload, extraction, validation, preservation, and persistence."""

import hashlib
import shutil
from pathlib import Path

from app.operational_data.extraction import RepositoryOperationalExtractor
from app.operational_data.models import (
    IssueSeverity,
    OperationalDomain,
    OperationalProcessingStatus,
    PopulationSourceBundle,
    PopulationSourceRole,
    ValidationIssue,
)
from app.operational_data.population_extraction import PopulationWorkbookExtractor
from app.operational_data.population_standardization import PopulationBundleStandardizer
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
        self.population_extractor = PopulationWorkbookExtractor()
        self.population_standardizer = PopulationBundleStandardizer()

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

    def ingest_population_bundle(
        self,
        sources: dict[PopulationSourceRole, tuple[Path, str]],
    ):
        """Validate, standardize, preserve and idempotently persist one population bundle."""

        extracted_sources = []
        source_checksums: dict[PopulationSourceRole, str] = {}
        for role, (source_path, filename) in sources.items():
            validate_operational_file(source_path, self.max_bytes)
            source_checksums[role] = hashlib.sha256(source_path.read_bytes()).hexdigest()
            extracted_sources.append(
                self.population_extractor.extract(source_path, role, filename)
            )
        report = self.population_standardizer.standardize(
            PopulationSourceBundle(sources=extracted_sources)
        )
        errors = [issue for issue in report.issues if issue.severity is IssueSeverity.ERROR]
        if report.processing_status is OperationalProcessingStatus.FAILED or errors:
            raise PopulationBundleProcessingError(
                "population bundle validation failed; source values were not persisted",
                errors,
            )

        combined_hasher = hashlib.sha256()
        for role in sorted(source_checksums, key=lambda item: item.value):
            combined_hasher.update(role.value.encode("utf-8"))
            combined_hasher.update(source_checksums[role].encode("ascii"))
        combined_checksum = combined_hasher.hexdigest()
        existing = self.repository.get(report.metadata.report_id)
        if existing:
            if existing.checksum_sha256 == combined_checksum:
                return existing, True
            raise PopulationBundleProcessingError(
                "a different bundle already exists for this organization and reporting period",
                [
                    ValidationIssue(
                        code="POP_BUSINESS_KEY_CONFLICT",
                        message=(
                            "Đã có báo cáo population khác nội dung cho cùng đơn vị và kỳ; "
                            "cần người dùng xác nhận trước khi thay thế."
                        ),
                        severity=IssueSeverity.ERROR,
                        field_path="metadata",
                    )
                ],
            )

        target_dir = (
            self.storage_dir
            / OperationalDomain.POPULATION.value
            / "bundles"
            / combined_checksum[:2]
            / combined_checksum
        )
        copied: list[Path] = []
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            for role, (source_path, filename) in sources.items():
                target = target_dir / f"{role.value.lower()}_{Path(filename).name}"
                shutil.copy2(source_path, target)
                copied.append(target)
            display_name = "population_bundle: " + " | ".join(
                sources[role][1] for role in sorted(sources, key=lambda item: item.value)
            )
            record = self.repository.save(
                report,
                filename=display_name,
                file_path=str(target_dir),
                checksum=combined_checksum,
            )
            return record, False
        except Exception:
            for target in copied:
                target.unlink(missing_ok=True)
            try:
                target_dir.rmdir()
            except OSError:
                pass
            raise


class PopulationBundleProcessingError(ValueError):
    """Structured population error returned as HTTP 422 by the API layer."""

    def __init__(self, message: str, issues: list[ValidationIssue]) -> None:
        super().__init__(message)
        self.issues = issues


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
