from pydantic import BaseModel, Field

from app.calculations.expressions import ComparisonOperator, ValueOperand
from app.operational_data.models import IssueSeverity, ValidationIssue


class RuleDefinition(BaseModel):
    rule_id: str = Field(min_length=1, max_length=128)
    operator: ComparisonOperator
    left: ValueOperand
    right: ValueOperand
    failure_message: str = Field(min_length=1, max_length=1000)
    severity: IssueSeverity = IssueSeverity.ERROR
    production_approved: bool = False
    label: str = "SYNTHETIC_NON_PRODUCTION_RULE"


class RuleEvaluationResult(BaseModel):
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    values_unchanged: bool = True
