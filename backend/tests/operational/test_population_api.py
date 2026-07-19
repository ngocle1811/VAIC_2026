from contextlib import ExitStack
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import Base, get_session
from app.main import app
from app.models.operational_report import OperationalReportRecord

DEMO = (
    Path(__file__).parents[3]
    / "ubnd_report_dataset"
    / "01_input_reports"
    / "population"
    / "normal"
    / "demo_case_1"
)
FILES = {
    "opening_balance_file": "01_so_du_dan_cu_dau_ky_2026-06.xlsx",
    "civil_status_file": "02_bao_cao_ho_tich_thang_06_2026.xlsx",
    "residence_movement_file": "03_bao_cao_bien_dong_cu_tru_06_2026.xlsx",
}
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def configured_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'population-api.db'}")
    Base.metadata.create_all(engine)
    settings = Settings(
        _env_file=None,
        database_url=str(engine.url),
        operational_storage_dir=tmp_path / "operational",
        report_output_dir=tmp_path / "reports",
    )

    def session_override():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), engine


def post_bundle(client):
    with ExitStack() as stack:
        files = {
            field: (filename, stack.enter_context((DEMO / filename).open("rb")), MIME)
            for field, filename in FILES.items()
        }
        return client.post("/operational-reports/population/bundle", files=files)


def test_population_bundle_api_returns_canonical_values_and_is_idempotent(tmp_path):
    client, engine = configured_client(tmp_path)
    try:
        response = post_bundle(client)
        assert response.status_code == 201
        body = response.json()
        assert body["canonical_values"]["population_closing"] == 12458
        assert body["calculated_values"] == {
            "population_closing": 12458,
            "temporary_closing": 1174,
        }
        assert body["validation"]["valid"] is True
        assert len(body["sources"]) == 3
        assert body["source_path_preserved"] is True
        assert post_bundle(client).json()["duplicate"] is True
        with Session(engine) as session:
            assert session.query(OperationalReportRecord).count() == 1
    finally:
        app.dependency_overrides.clear()


def test_population_bundle_api_rejects_missing_file_without_persistence(tmp_path):
    client, engine = configured_client(tmp_path)
    try:
        source = DEMO / FILES["opening_balance_file"]
        with source.open("rb") as handle:
            response = client.post(
                "/operational-reports/population/bundle",
                files={"opening_balance_file": (source.name, handle, MIME)},
            )
        assert response.status_code == 422
        with Session(engine) as session:
            assert session.query(OperationalReportRecord).count() == 0
    finally:
        app.dependency_overrides.clear()
