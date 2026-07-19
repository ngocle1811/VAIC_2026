"""Synthetic-only deterministic KPIs for the repository test fixtures."""

from decimal import Decimal, DivisionByZero, InvalidOperation

from app.operational_data.models import DataClassification, OperationalDomain


def _decimal(values: dict, name: str) -> Decimal:
    try:
        return Decimal(str(values[name]))
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise ValueError(f"numeric source field is unavailable: {name}") from exc


def calculate_fixture_kpis(domain: OperationalDomain, classification: str, values: dict) -> dict:
    if classification != DataClassification.SYNTHETIC_TEST_DATA.value:
        raise ValueError("official KPI definitions are not approved")
    try:
        if domain is OperationalDomain.POPULATION:
            if "population_opening" in values:
                start = _decimal(values, "population_opening")
                end = _decimal(values, "population_closing")
                temporary_start = _decimal(values, "temporary_opening")
                temporary_end = _decimal(values, "temporary_closing")
                birth_registered = _decimal(values, "birth_registered")
                birth_local = _decimal(values, "birth_local_resident")
                death_registered = _decimal(values, "death_registered")
                death_local = _decimal(values, "death_local_resident")
                return {
                    "population_net_change": end - start,
                    "population_change_rate_percent": (end - start) * 100 / start,
                    "permanent_net_migration": _decimal(values, "permanent_in")
                    - _decimal(values, "permanent_out"),
                    "temporary_net_change": temporary_end - temporary_start,
                    "birth_registered_count": birth_registered,
                    "birth_local_resident_count": birth_local,
                    "birth_registered_outside_local_residence": birth_registered - birth_local,
                    "death_registered_count": death_registered,
                    "death_local_resident_count": death_local,
                    "death_registered_outside_local_residence": death_registered - death_local,
                }
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
