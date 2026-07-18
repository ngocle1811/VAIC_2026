"""Synthetic-only deterministic KPIs for the repository test fixtures."""

from decimal import Decimal, DivisionByZero, InvalidOperation

from app.operational_data.models import DataClassification, OperationalDomain


def _decimal(values: dict, name: str) -> Decimal:
    try:
        return Decimal(str(values[name]))
    except (KeyError, InvalidOperation) as exc:
        raise ValueError(f"numeric source field is unavailable: {name}") from exc


def calculate_fixture_kpis(domain: OperationalDomain, classification: str, values: dict) -> dict:
    if classification != DataClassification.SYNTHETIC_TEST_DATA.value:
        raise ValueError("official KPI definitions are not approved")
    try:
        if domain is OperationalDomain.POPULATION:
            start = _decimal(values, "population_start")
            end = _decimal(values, "population_total")
            return {
                "population_net_change": end - start,
                "population_change_rate_percent": (end - start) * 100 / start,
            }
        if domain is OperationalDomain.COMPLAINTS:
            return {
                "complaint_resolution_rate_percent": _decimal(values, "resolved_cases")
                * 100
                / _decimal(values, "received_cases")
            }
        return {
            "task_completion_rate_percent": (
                _decimal(values, "completed_on_time") + _decimal(values, "completed_late")
            )
            * 100
            / _decimal(values, "task_total"),
            "task_average_progress_percent": _decimal(values, "average_progress"),
        }
    except (DivisionByZero, ZeroDivisionError) as exc:
        raise ValueError("KPI denominator must be non-zero") from exc
