"""Apply whitelisted comparisons while preserving the source report."""

from copy import deepcopy

from app.calculations.expressions import compare, resolve
from app.operational_data.models import DataClassification, OperationalReport, ValidationIssue
from app.rules.models import RuleDefinition, RuleEvaluationResult


class RuleEngine:
    def evaluate(
        self, report: OperationalReport, definitions: list[RuleDefinition]
    ) -> RuleEvaluationResult:
        before = deepcopy(report.values)
        issues = []
        for definition in definitions:
            if (
                report.metadata.classification != DataClassification.SYNTHETIC_TEST_DATA
                and not definition.production_approved
            ):
                raise ValueError("non-production rules require synthetic test data")
            passed = compare(
                definition.operator,
                resolve(definition.left, report.values),
                resolve(definition.right, report.values),
            )
            if not passed:
                issues.append(
                    ValidationIssue(
                        code=definition.rule_id,
                        message=definition.failure_message,
                        severity=definition.severity,
                        field_path=definition.left.field,
                    )
                )
        unchanged = before == report.values
        if not unchanged:
            raise RuntimeError("rule evaluation modified operational source values")
        return RuleEvaluationResult(passed=not issues, issues=issues, values_unchanged=True)
