"""Deterministic validation limited to explicitly synthetic repository fixtures."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation

from app.operational_data.models import (
    DataClassification,
    IssueSeverity,
    OperationalDomain,
    OperationalReport,
    OperationalValidationResult,
    ValidationIssue,
)


def _number(value: object) -> Decimal | None:
    try:
        return None if value is None else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _issue(code: str, message: str, field: str, severity=IssueSeverity.ERROR):
    return ValidationIssue(code=code, message=message, field_path=field, severity=severity)


class SyntheticOperationalValidator:
    """Apply only fixture-encoded identities; never promote them to official rules."""

    def validate(self, report: OperationalReport) -> OperationalValidationResult:
        candidate = report.model_copy(deep=True)
        if report.metadata.classification is not DataClassification.SYNTHETIC_TEST_DATA:
            warning = _issue(
                "OFFICIAL_RULES_UNAVAILABLE",
                "Official validation rules are unavailable; human review is required.",
                "metadata.classification",
                IssueSeverity.WARNING,
            )
            return OperationalValidationResult(report=candidate, warnings=[warning])
        before = deepcopy(candidate.values)
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        domain = candidate.metadata.domain
        if domain is OperationalDomain.POPULATION:
            self._population(candidate, errors)
        elif domain is OperationalDomain.COMPLAINTS:
            self._complaints(candidate, errors)
        else:
            self._tasks(candidate, errors, warnings)
        if before != candidate.values:
            raise RuntimeError("validation modified source values")
        return OperationalValidationResult(report=candidate, errors=errors, warnings=warnings)

    @staticmethod
    def _required(report, fields, errors):
        for field in fields:
            if report.values.get(field) is None:
                errors.append(_issue("REQUIRED_FIELD_MISSING", "Thiếu trường bắt buộc.", field))

    def _population(self, report, errors):
        required = [
            "population_start",
            "arrivals",
            "departures",
            "births",
            "deaths",
            "population_total",
            "male",
            "female",
            "permanent",
            "temporary",
        ]
        self._required(report, required, errors)
        values = {field: _number(report.values.get(field)) for field in required}
        if all(values[field] is not None for field in required[:6]):
            expected = (
                values["population_start"]
                + values["arrivals"]
                - values["departures"]
                + values["births"]
                - values["deaths"]
            )
            if expected != values["population_total"]:
                errors.append(
                    _issue(
                        "POP_BALANCE_MISMATCH",
                        "Dân số cuối kỳ không khớp biến động.",
                        "population_total",
                    )
                )
        for left, right, code in (
            (("male", "female"), "population_total", "POP_GENDER_TOTAL_MISMATCH"),
            (("permanent", "temporary"), "population_total", "POP_RESIDENCE_TOTAL_MISMATCH"),
        ):
            if (
                all(values[item] is not None for item in (*left, right))
                and sum(values[item] for item in left) != values[right]
            ):
                errors.append(_issue(code, "Tổng thành phần không khớp dân số cuối kỳ.", right))

    def _complaints(self, report, errors):
        required = [
            "received_cases",
            "complaint_cases",
            "denunciation_cases",
            "petition_cases",
            "within_authority",
            "outside_authority",
            "resolved_cases",
        ]
        self._required(report, required, errors)
        values = {field: _number(report.values.get(field)) for field in report.values}
        received = values.get("received_cases")
        for fields, code in (
            (
                ("complaint_cases", "denunciation_cases", "petition_cases"),
                "COM_TYPE_TOTAL_MISMATCH",
            ),
            (("within_authority", "outside_authority"), "COM_AUTHORITY_TOTAL_MISMATCH"),
        ):
            if received is not None and all(values.get(item) is not None for item in fields):
                if sum(values[item] for item in fields) != received:
                    errors.append(
                        _issue(
                            code, "Tổng phân loại không khớp số đơn tiếp nhận.", "received_cases"
                        )
                    )
        balance = ("beginning_cases", "received_cases", "resolved_cases", "ending_cases")
        if all(values.get(item) is not None for item in balance):
            if (
                values["beginning_cases"] + received - values["resolved_cases"]
                != values["ending_cases"]
            ):
                errors.append(
                    _issue("COM_BALANCE_MISMATCH", "Đơn tồn cuối kỳ không khớp.", "ending_cases")
                )

    def _tasks(self, report, errors, warnings):
        if not report.records:
            errors.append(
                _issue("TASK_LIST_MISSING", "Không tìm thấy danh sách nhiệm vụ.", "records")
            )
            return
        as_of = report.metadata.reporting_period.end
        for index, record in enumerate(report.records):
            prefix = f"records[{index}]"
            if not record.get("lead_unit"):
                errors.append(
                    _issue(
                        "TASK_LEAD_UNIT_REQUIRED",
                        "Nhiệm vụ phải có đơn vị chủ trì.",
                        f"{prefix}.lead_unit",
                    )
                )
            progress = _number(record.get("progress_percent"))
            if progress is None:
                warnings.append(
                    _issue(
                        "TASK_PROGRESS_MISSING",
                        "Thiếu tiến độ.",
                        f"{prefix}.progress_percent",
                        IssueSeverity.WARNING,
                    )
                )
            elif not 0 <= progress <= 100:
                errors.append(
                    _issue(
                        "TASK_PROGRESS_RANGE",
                        "Tiến độ phải từ 0 đến 100.",
                        f"{prefix}.progress_percent",
                    )
                )
            assigned = record.get("assignment_date")
            completed = record.get("completion_date")
            due = record.get("due_date")
            if isinstance(assigned, date) and isinstance(completed, date) and completed < assigned:
                errors.append(
                    _issue(
                        "TASK_COMPLETION_BEFORE_ASSIGNMENT",
                        "Ngày hoàn thành không được trước ngày giao.",
                        f"{prefix}.completion_date",
                    )
                )
            status = str(record.get("status") or "").casefold()
            is_completed = status.startswith("hoàn thành")
            if is_completed and not record.get("completion_result"):
                errors.append(
                    _issue(
                        "TASK_RESULT_REQUIRED",
                        "Nhiệm vụ hoàn thành phải có kết quả.",
                        f"{prefix}.completion_result",
                    )
                )
            if (
                isinstance(due, date)
                and due < as_of
                and not completed
                and not is_completed
                and "quá hạn" not in status
            ):
                warnings.append(
                    _issue(
                        "TASK_OVERDUE_STATUS",
                        "Nhiệm vụ quá hạn phải được đánh dấu quá hạn.",
                        f"{prefix}.status",
                        IssueSeverity.WARNING,
                    )
                )
            if (
                isinstance(due, date)
                and isinstance(completed, date)
                and completed > due
                and "quá hạn" not in status
            ):
                errors.append(
                    _issue(
                        "TASK_COMPLETED_LATE_STATUS",
                        "Hoàn thành sau hạn phải có trạng thái hoàn thành quá hạn.",
                        f"{prefix}.status",
                    )
                )
