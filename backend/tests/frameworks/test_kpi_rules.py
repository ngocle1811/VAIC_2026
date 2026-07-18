from copy import deepcopy

import pytest

from app.calculations.expressions import (
    ArithmeticOperator,
    ComparisonOperator,
    ValueOperand,
)
from app.kpi.engine import KPIEngine
from app.kpi.models import KPIDefinition
from app.operational_data.models import DataClassification
from app.rules.engine import RuleEngine
from app.rules.models import RuleDefinition


def test_kpi_uses_whitelisted_arithmetic_and_source_fields(synthetic_report) -> None:
    definition = KPIDefinition(
        kpi_id="synthetic_difference",
        operator=ArithmeticOperator.SUBTRACT,
        left=ValueOperand(field="metric_alpha"),
        right=ValueOperand(field="metric_beta"),
    )
    result = KPIEngine().calculate(synthetic_report, definition)
    assert result.value == 5
    assert result.source_fields == ["metric_alpha", "metric_beta"]
    with pytest.raises(ValueError, match="division by zero"):
        KPIEngine().calculate(
            synthetic_report,
            definition.model_copy(
                update={
                    "operator": ArithmeticOperator.DIVIDE,
                    "right": ValueOperand(constant=0),
                }
            ),
        )


def test_rule_engine_is_deterministic_and_never_changes_values(synthetic_report) -> None:
    before = deepcopy(synthetic_report.values)
    rule = RuleDefinition(
        rule_id="synthetic_compare",
        operator=ComparisonOperator.GREATER_OR_EQUAL,
        left=ValueOperand(field="metric_alpha"),
        right=ValueOperand(field="metric_beta"),
        failure_message="Synthetic comparison failed",
    )
    result = RuleEngine().evaluate(synthetic_report, [rule])
    assert result.passed and result.values_unchanged
    assert synthetic_report.values == before

    official_candidate = synthetic_report.model_copy(deep=True)
    official_candidate.metadata.classification = DataClassification.OFFICIAL_CANDIDATE
    with pytest.raises(ValueError, match="synthetic test data"):
        RuleEngine().evaluate(official_candidate, [rule])
