from decimal import Decimal

from pydantic import BaseModel, Field

from app.calculations.expressions import ArithmeticOperator, ValueOperand


class KPIDefinition(BaseModel):
    kpi_id: str = Field(min_length=1, max_length=128)
    operator: ArithmeticOperator
    left: ValueOperand
    right: ValueOperand
    production_approved: bool = False
    label: str = "SYNTHETIC_NON_PRODUCTION_RULE"


class KPIResult(BaseModel):
    kpi_id: str
    value: Decimal
    source_fields: list[str] = Field(default_factory=list)
    definition_label: str
