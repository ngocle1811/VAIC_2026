from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.operational_data.models import PopulationSourceRole
from app.operational_data.population_extraction import (
    PopulationExtractionError,
    PopulationWorkbookExtractor,
)

DEMO = (
    Path(__file__).parents[3]
    / "ubnd_report_dataset"
    / "01_input_reports"
    / "population"
    / "normal"
    / "demo_case_1"
)

SOURCES = {
    PopulationSourceRole.OPENING_BALANCE: "01_so_du_dan_cu_dau_ky_2026-06.xlsx",
    PopulationSourceRole.CIVIL_STATUS: "02_bao_cao_ho_tich_thang_06_2026.xlsx",
    PopulationSourceRole.RESIDENCE_MOVEMENT: "03_bao_cao_bien_dong_cu_tru_06_2026.xlsx",
}


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (
            PopulationSourceRole.OPENING_BALANCE,
            {"population_opening": 12430, "temporary_opening": 1120},
        ),
        (
            PopulationSourceRole.CIVIL_STATUS,
            {
                "birth_registered": 20,
                "birth_local_resident": 18,
                "death_registered": 8,
                "death_local_resident": 7,
            },
        ),
        (
            PopulationSourceRole.RESIDENCE_MOVEMENT,
            {
                "permanent_in": 42,
                "permanent_out": 25,
                "temporary_new": 85,
                "temporary_removed": 31,
            },
        ),
    ],
)
def test_population_workbook_roles_and_detail_counts(role, expected):
    source = PopulationWorkbookExtractor().extract(DEMO / SOURCES[role], role)
    assert source.role is role
    assert source.values == expected
    assert source.detail_counts == expected
    assert source.reporting_period.label == "Tháng 06/2026"
    assert source.organization.organization_name == "UBND xã An Bình"


def test_source_role_is_detected_from_content_not_filename():
    source = DEMO / SOURCES[PopulationSourceRole.OPENING_BALANCE]
    extracted = PopulationWorkbookExtractor().extract(source)
    assert extracted.role is PopulationSourceRole.OPENING_BALANCE
    with pytest.raises(PopulationExtractionError) as captured:
        PopulationWorkbookExtractor().extract(source, PopulationSourceRole.CIVIL_STATUS)
    assert captured.value.issues[0].code == "POP_SOURCE_ROLE_MISMATCH"


def test_summary_detail_mismatch_is_rejected(tmp_path):
    source = DEMO / SOURCES[PopulationSourceRole.CIVIL_STATUS]
    changed = tmp_path / "civil_status_mismatch.xlsx"
    workbook = load_workbook(source)
    workbook["Tong_hop"]["C11"] = 21
    workbook.save(changed)
    workbook.close()

    with pytest.raises(PopulationExtractionError) as captured:
        PopulationWorkbookExtractor().extract(changed)
    assert {issue.code for issue in captured.value.issues} == {
        "POP_SUMMARY_DETAIL_MISMATCH"
    }
