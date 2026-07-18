"""Whitelisted arithmetic and comparison operators; no expression evaluation."""

from decimal import Decimal, InvalidOperation
from enum import StrEnum

from pydantic import BaseModel, model_validator

from app.operational_data.models import OperationalScalar


class ArithmeticOperator(StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class ComparisonOperator(StrEnum):
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER_THAN = "greater_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_THAN = "less_than"
    LESS_OR_EQUAL = "less_or_equal"


class ValueOperand(BaseModel):
    field: str | None = None
    constant: OperationalScalar = None

    @model_validator(mode="after")
    def require_one_source(self) -> "ValueOperand":
        if (self.field is None) == (self.constant is None):
            raise ValueError("operand requires exactly one field or non-null constant")
        return self


def resolve(operand: ValueOperand, values: dict[str, OperationalScalar]) -> OperationalScalar:
    if operand.field is not None:
        if operand.field not in values:
            raise KeyError(f"missing operational field: {operand.field}")
        return values[operand.field]
    return operand.constant


def decimal_value(value: OperationalScalar) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("numeric operation requires a number")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("numeric operation requires a number") from exc


def arithmetic(operator: ArithmeticOperator, left: Decimal, right: Decimal) -> Decimal:
    operations = {
        ArithmeticOperator.ADD: lambda: left + right,
        ArithmeticOperator.SUBTRACT: lambda: left - right,
        ArithmeticOperator.MULTIPLY: lambda: left * right,
        ArithmeticOperator.DIVIDE: lambda: left / right,
    }
    if operator == ArithmeticOperator.DIVIDE and right == 0:
        raise ValueError("division by zero")
    return operations[operator]()


def compare(
    operator: ComparisonOperator, left: OperationalScalar, right: OperationalScalar
) -> bool:
    if operator == ComparisonOperator.EQUAL:
        return left == right
    if operator == ComparisonOperator.NOT_EQUAL:
        return left != right
    left_number = decimal_value(left)
    right_number = decimal_value(right)
    operations = {
        ComparisonOperator.GREATER_THAN: left_number > right_number,
        ComparisonOperator.GREATER_OR_EQUAL: left_number >= right_number,
        ComparisonOperator.LESS_THAN: left_number < right_number,
        ComparisonOperator.LESS_OR_EQUAL: left_number <= right_number,
    }
    return operations[operator]
