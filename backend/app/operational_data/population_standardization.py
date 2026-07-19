"""Merge and validate the three deterministic population source roles."""

from __future__ import annotations

from collections import Counter
from uuid import NAMESPACE_URL, uuid5

from app.operational_data.models import (
    CommonReportMetadata,
    DataClassification,
    IssueSeverity,
    OperationalDomain,
    OperationalProcessingStatus,
    OperationalReport,
    PopulationReportValues,
    PopulationSourceBundle,
    PopulationSourceRole,
    ValidationIssue,
)
from app.operational_data.population_extraction import ROLE_FIELDS
from app.operational_data.validation import PopulationCanonicalValidator


class PopulationStandardizationError(ValueError):
    """Raised with structured issues for an invalid or ambiguous bundle."""

    def __init__(self, message: str, issues: list[ValidationIssue]) -> None:
        super().__init__(message)
        self.issues = issues


def _error(code: str, message: str, field: str) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        severity=IssueSeverity.ERROR,
        field_path=field,
    )


class PopulationBundleStandardizer:
    """Build one canonical report without mutating any source workbook values."""

    def standardize(self, bundle: PopulationSourceBundle) -> OperationalReport:
        self._validate_bundle_identity(bundle)
        first = bundle.sources[0]
        merged: dict[str, int] = {}
        provenance = {}
        source_records: list[dict] = []
        source_warnings: list[ValidationIssue] = []

        for source in bundle.sources:
            for field, value in source.values.items():
                if field in merged and merged[field] != value:
                    raise PopulationStandardizationError(
                        "conflicting canonical values were supplied",
                        [
                            _error(
                                "POP_CANONICAL_FIELD_CONFLICT",
                                f"Hai nguồn cung cấp {field} với giá trị khác nhau.",
                                field,
                            )
                        ],
                    )
                merged[field] = value
                provenance[field] = source.provenance.get(field, [])
            source_warnings.extend(source.extraction_warnings)
            source_records.append(
                {
                    "record_type": "population_source",
                    "source_file_id": source.source_filename,
                    "source_role": source.role.value,
                    "reporting_period": source.reporting_period.label,
                    "organization_id": source.organization.organization_id,
                    "organization_name": source.organization.organization_name,
                    "sheet_name": ", ".join(source.sheet_names),
                    "detail_record_count": source.detail_record_count,
                    "extraction_warnings": ", ".join(
                        warning.code for warning in source.extraction_warnings
                    )
                    or None,
                }
            )
            for field, value in source.detail_counts.items():
                source_records.append(
                    {
                        "record_type": "population_detail_count",
                        "source_file_id": source.source_filename,
                        "source_role": source.role.value,
                        "field": field,
                        "value": value,
                    }
                )

        required_inputs = set().union(*ROLE_FIELDS.values())
        missing = sorted(required_inputs - set(merged))
        if missing:
            raise PopulationStandardizationError(
                "population bundle is missing canonical input fields",
                [
                    _error("POP_REQUIRED_FIELD_MISSING", "Thiếu trường bắt buộc.", field)
                    for field in missing
                ],
            )

        merged["population_closing"] = (
            merged["population_opening"]
            + merged["birth_local_resident"]
            + merged["permanent_in"]
            - merged["death_local_resident"]
            - merged["permanent_out"]
        )
        merged["temporary_closing"] = (
            merged["temporary_opening"]
            + merged["temporary_new"]
            - merged["temporary_removed"]
        )
        for closing, fields in {
            "population_closing": (
                "population_opening",
                "birth_local_resident",
                "permanent_in",
                "death_local_resident",
                "permanent_out",
            ),
            "temporary_closing": (
                "temporary_opening",
                "temporary_new",
                "temporary_removed",
            ),
        }.items():
            provenance[closing] = [item for field in fields for item in provenance.get(field, [])]

        classifications = {source.classification for source in bundle.sources}
        classification = (
            DataClassification.SYNTHETIC_TEST_DATA
            if classifications == {DataClassification.SYNTHETIC_TEST_DATA}
            else DataClassification.OFFICIAL_CANDIDATE
        )
        business_key = (
            f"population-bundle:{first.organization.organization_id}:"
            f"{first.reporting_period.start.isoformat()}:{first.reporting_period.end.isoformat()}"
        )
        report = OperationalReport(
            metadata=CommonReportMetadata(
                report_id=str(uuid5(NAMESPACE_URL, business_key)),
                domain=OperationalDomain.POPULATION,
                reporting_period=first.reporting_period,
                organization=first.organization,
                classification=classification,
                schema_version="population-canonical-v1",
            ),
            values=merged,
            provenance=provenance,
            records=source_records,
            processing_status=OperationalProcessingStatus.EXTRACTED,
        )
        result = PopulationCanonicalValidator().validate(report)
        issues = result.errors + source_warnings + result.warnings
        status = (
            OperationalProcessingStatus.FAILED
            if result.errors
            else (
                OperationalProcessingStatus.NEEDS_REVIEW
                if source_warnings or result.warnings
                else OperationalProcessingStatus.VALIDATED
            )
        )
        validated = result.report.model_copy(update={"issues": issues, "processing_status": status})
        if not result.errors:
            typed_values = PopulationReportValues(**validated.values).model_dump()
            validated = validated.model_copy(update={"values": typed_values})
        return validated

    @staticmethod
    def _validate_bundle_identity(bundle: PopulationSourceBundle) -> None:
        roles = Counter(source.role for source in bundle.sources)
        issues: list[ValidationIssue] = []
        for role in PopulationSourceRole:
            count = roles[role]
            if count == 0:
                issues.append(
                    _error(
                        "POP_SOURCE_ROLE_MISSING",
                        f"Thiếu nguồn {role.value}.",
                        "sources",
                    )
                )
            elif count > 1:
                issues.append(
                    _error(
                        "POP_SOURCE_ROLE_DUPLICATE",
                        f"Nguồn {role.value} xuất hiện {count} lần.",
                        "sources",
                    )
                )
        unknown_count = len(bundle.sources) - sum(roles[role] for role in PopulationSourceRole)
        if unknown_count or len(bundle.sources) != 3:
            issues.append(
                _error(
                    "POP_SOURCE_COUNT_INVALID",
                    "Bundle population phải gồm đúng ba source role.",
                    "sources",
                )
            )

        periods = {
            (
                source.reporting_period.kind,
                source.reporting_period.start,
                source.reporting_period.end,
            )
            for source in bundle.sources
        }
        if len(periods) > 1:
            issues.append(
                _error(
                    "POP_REPORTING_PERIOD_MISMATCH",
                    "Ba nguồn không cùng kỳ báo cáo.",
                    "sources.reporting_period",
                )
            )
        organizations = {source.organization.organization_id for source in bundle.sources}
        if len(organizations) > 1:
            issues.append(
                _error(
                    "POP_REPORTING_ORGANIZATION_MISMATCH",
                    "Ba nguồn không cùng đơn vị tổng hợp.",
                    "sources.organization",
                )
            )
        if issues:
            raise PopulationStandardizationError("invalid population source bundle", issues)
