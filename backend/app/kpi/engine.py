"""Calculate only explicitly supplied, whitelisted KPI definitions."""

from app.calculations.expressions import arithmetic, decimal_value, resolve
from app.kpi.models import KPIDefinition, KPIResult
from app.operational_data.models import DataClassification, OperationalReport


class KPIEngine:
    def calculate(self, report: OperationalReport, definition: KPIDefinition) -> KPIResult:
        if (
            report.metadata.classification != DataClassification.SYNTHETIC_TEST_DATA
            and not definition.production_approved
        ):
            raise ValueError("non-production KPI definitions require synthetic test data")
        left = decimal_value(resolve(definition.left, report.values))
        right = decimal_value(resolve(definition.right, report.values))
        fields = [item for item in (definition.left.field, definition.right.field) if item]
        return KPIResult(
            kpi_id=definition.kpi_id,
            value=arithmetic(definition.operator, left, right),
            source_fields=fields,
            definition_label=definition.label,
        )
