from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import Base, get_session
from app.main import app

DATASET = Path(__file__).parents[3] / "ubnd_report_dataset" / "01_input_reports"


@pytest.mark.e2e
def test_offline_api_workflow_with_fake_provider(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}")
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
    client = TestClient(app)
    source = DATASET / "population/normal/bao_cao_dan_cu_thang_04_2026.xlsx"
    try:
        with source.open("rb") as handle:
            upload = client.post(
                "/operational-reports?domain=population",
                files={
                    "file": (
                        source.name,
                        handle,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
        assert upload.status_code == 201
        report_id = upload.json()["report_id"]
        assert upload.json()["source_path_preserved"] is True
        assert client.get(f"/operational-reports/{report_id}").status_code == 200
        assert (
            "population_net_change"
            in client.get(f"/operational-reports/{report_id}/kpis").json()["kpis"]
        )

        agent = client.post(
            "/agent/analyze",
            json={"report_id": report_id, "user_request": "Kiểm tra KPI và tạo báo cáo"},
        )
        assert agent.status_code == 200
        assert agent.json()["state"]["operational_data"]["report_id"] == report_id
        assert agent.json()["state"]["human_review_required"] is True

        generated = client.post(
            "/reports",
            json={"operational_report_id": report_id, "template_id": "synthetic_domain_draft"},
        )
        assert generated.status_code == 200
        generated_id = generated.json()["report_id"]
        assert generated.json()["status"] == "needs_review"
        assert client.get(f"/reports/{generated_id}/download").status_code == 200
        reviewed = client.post(
            f"/reviews/{generated_id}",
            json={"decision": "approved", "reviewer": "test-reviewer"},
        )
        assert reviewed.json()["status"] == "approved"
    finally:
        app.dependency_overrides.clear()


def test_upload_rejects_extension_signature_mismatch(tmp_path):
    class RejectingService:
        def ingest(self, source_path, original_filename, domain):
            from app.security.file_validation import validate_operational_file

            validate_operational_file(source_path, 1024)

    from app.api.routes.operational_reports import get_operational_service

    app.dependency_overrides[get_operational_service] = lambda: RejectingService()
    client = TestClient(app)
    try:
        response = client.post(
            "/operational-reports?domain=population",
            files={"file": ("malware.pdf", b"MZ executable", "application/pdf")},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
