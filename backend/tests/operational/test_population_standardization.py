from datetime import date
from pathlib import Path

import pytest

from app.operational_data.models import PopulationSourceBundle, PopulationSourceRole
from app.operational_data.population_extraction import PopulationWorkbookExtractor
from app.operational_data.population_standardization import (
    PopulationBundleStandardizer,
    PopulationStandardizationError,
)

DEMO = (
    Path(__file__).parents[3]
    / "ubnd_report_dataset"
    / "01_input_reports"
    / "population"
    / "normal"
    / "demo_case_1"
)
FILES = (
    (PopulationSourceRole.OPENING_BALANCE, "01_so_du_dan_cu_dau_ky_2026-06.xlsx"),
    (PopulationSourceRole.CIVIL_STATUS, "02_bao_cao_ho_tich_thang_06_2026.xlsx"),
    (
        PopulationSourceRole.RESIDENCE_MOVEMENT,
        "03_bao_cao_bien_dong_cu_tru_06_2026.xlsx",
    ),
)


def extracted_sources():
    extractor = PopulationWorkbookExtractor()
    return [extractor.extract(DEMO / filename, role) for role, filename in FILES]


def test_standardizer_calculates_canonical_closing_values():
    report = PopulationBundleStandardizer().standardize(
        PopulationSourceBundle(sources=extracted_sources())
    )
    assert report.values == {
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
    assert report.metadata.schema_version == "population-canonical-v1"
    assert {issue.code for issue in report.issues} >= {
        "POP_BIRTH_REGISTRATION_SCOPE_DIFFERS",
        "POP_DEATH_REGISTRATION_SCOPE_DIFFERS",
    }


def test_missing_and_duplicate_source_roles_are_rejected():
    sources = extracted_sources()
    with pytest.raises(PopulationStandardizationError) as missing:
        PopulationBundleStandardizer().standardize(
            PopulationSourceBundle(sources=sources[:2])
        )
    assert "POP_SOURCE_ROLE_MISSING" in {issue.code for issue in missing.value.issues}

    with pytest.raises(PopulationStandardizationError) as duplicate:
        PopulationBundleStandardizer().standardize(
            PopulationSourceBundle(sources=[sources[0], sources[0], sources[2]])
        )
    codes = {issue.code for issue in duplicate.value.issues}
    assert {"POP_SOURCE_ROLE_DUPLICATE", "POP_SOURCE_ROLE_MISSING"} <= codes


def test_reporting_period_mismatch_is_rejected():
    sources = extracted_sources()
    wrong_period = sources[1].reporting_period.model_copy(
        update={"start": date(2026, 5, 1), "end": date(2026, 5, 31)}
    )
    sources[1] = sources[1].model_copy(update={"reporting_period": wrong_period})
    with pytest.raises(PopulationStandardizationError) as captured:
        PopulationBundleStandardizer().standardize(PopulationSourceBundle(sources=sources))
    assert "POP_REPORTING_PERIOD_MISMATCH" in {
        issue.code for issue in captured.value.issues
    }


def test_conflicting_canonical_field_is_rejected():
    sources = extracted_sources()
    sources[1] = sources[1].model_copy(
        update={"values": {**sources[1].values, "population_opening": 999}}
    )
    with pytest.raises(PopulationStandardizationError) as captured:
        PopulationBundleStandardizer().standardize(PopulationSourceBundle(sources=sources))
    assert captured.value.issues[0].code == "POP_CANONICAL_FIELD_CONFLICT"
