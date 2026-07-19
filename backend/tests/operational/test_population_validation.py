from copy import deepcopy
from datetime import date

import pytest
from pydantic import ValidationError

from app.operational_data.models import (
    CommonReportMetadata,
    DataClassification,
    OperationalDomain,
    OperationalReport,
    OrganizationMetadata,
    PopulationReportValues,
    ReportingPeriod,
    ReportingPeriodKind,
)
from app.operational_data.validation import PopulationCanonicalValidator


def report_with(**updates):
    values = {
        "population_opening": 12430,
        "population_closing": 12458,
        "birth_registered": 20,
        "birth_local_resident": 18,
        "death_registered": 8,
        "death_local_resident": 7,
        "permanent_in": 42,
        "permanent_out": 25,
        "temporary_opening": 1120,
        "temporary_new": 85,
        "temporary_removed": 31,
        "temporary_closing": 1174,
    }
    values.update(updates)
    return OperationalReport(
        metadata=CommonReportMetadata(
            report_id="population-validation-test",
            domain=OperationalDomain.POPULATION,
            reporting_period=ReportingPeriod(
                kind=ReportingPeriodKind.MONTH,
                start=date(2026, 6, 1),
                end=date(2026, 6, 30),
            ),
            organization=OrganizationMetadata(
                organization_id="test-unit", organization_name="Synthetic Test Unit"
            ),
            classification=DataClassification.SYNTHETIC_TEST_DATA,
        ),
        values=values,
    )


def test_canonical_formulas_are_valid_and_source_values_are_unchanged():
    report = report_with()
    before = deepcopy(report.values)
    result = PopulationCanonicalValidator().validate(report)
    assert result.valid
    assert result.report.values == before


def test_registered_and_local_resident_counts_are_not_interchangeable():
    result = PopulationCanonicalValidator().validate(
        report_with(birth_local_resident=21, death_local_resident=9)
    )
    assert {
        "POP_BIRTH_LOCAL_EXCEEDS_REGISTERED",
        "POP_DEATH_LOCAL_EXCEEDS_REGISTERED",
    } <= {issue.code for issue in result.errors}


def test_both_closing_formula_mismatches_are_reported():
    result = PopulationCanonicalValidator().validate(
        report_with(population_closing=12459, temporary_closing=1175)
    )
    assert {
        "POP_CANONICAL_BALANCE_MISMATCH",
        "POP_TEMPORARY_BALANCE_MISMATCH",
    } == {issue.code for issue in result.errors}


def test_typed_values_reject_negative_numbers_but_preserve_nulls():
    values = PopulationReportValues(population_opening=None)
    assert values.population_opening is None
    with pytest.raises(ValidationError):
        PopulationReportValues(population_opening=-1)
