"""Thin APIs for operational ingestion, querying, validation outcomes, and fixture KPIs."""

import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_session
from app.kpi.catalog import calculate_fixture_kpis
from app.operational_data.extraction import OperationalExtractionError
from app.operational_data.models import IssueSeverity, OperationalDomain, PopulationSourceRole
from app.operational_data.pipeline import (
    OperationalPipelineService,
    PopulationBundleProcessingError,
    record_payload,
)
from app.operational_data.population_extraction import PopulationExtractionError
from app.operational_data.population_standardization import PopulationStandardizationError
from app.operational_data.repository import SqlOperationalReportRepository
from app.security.file_validation import UnsafeUploadError

router = APIRouter(prefix="/operational-reports", tags=["operational-reports"])


def get_operational_service(
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OperationalPipelineService:
    return OperationalPipelineService(
        SqlOperationalReportRepository(session),
        settings.operational_storage_dir,
        settings.max_document_size_mb,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_operational_report(
    domain: OperationalDomain,
    file: Annotated[UploadFile, File()],
    service: Annotated[OperationalPipelineService, Depends(get_operational_service)],
):
    suffix = Path(file.filename or "upload").suffix
    temporary_path = None
    try:
        with NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            shutil.copyfileobj(file.file, temporary)
            temporary_path = Path(temporary.name)
        record, duplicate = service.ingest(temporary_path, file.filename or "upload", domain)
        return {**record_payload(record), "duplicate": duplicate, "source_path_preserved": True}
    except (UnsafeUploadError, OperationalExtractionError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)


@router.post("/population/bundle", status_code=status.HTTP_201_CREATED)
def upload_population_bundle(
    opening_balance_file: Annotated[UploadFile, File()],
    civil_status_file: Annotated[UploadFile, File()],
    residence_movement_file: Annotated[UploadFile, File()],
    service: Annotated[OperationalPipelineService, Depends(get_operational_service)],
):
    """Ingest exactly three structurally identified population XLSX sources."""

    uploads = {
        PopulationSourceRole.OPENING_BALANCE: opening_balance_file,
        PopulationSourceRole.CIVIL_STATUS: civil_status_file,
        PopulationSourceRole.RESIDENCE_MOVEMENT: residence_movement_file,
    }
    temporary_paths: dict[PopulationSourceRole, Path] = {}
    try:
        for role, upload in uploads.items():
            suffix = Path(upload.filename or "upload.xlsx").suffix
            with NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
                shutil.copyfileobj(upload.file, temporary)
                temporary_paths[role] = Path(temporary.name)
        record, duplicate = service.ingest_population_bundle(
            {
                role: (temporary_paths[role], upload.filename or "upload.xlsx")
                for role, upload in uploads.items()
            }
        )
        payload = record_payload(record)
        validation_messages = record.issues
        return {
            **payload,
            "canonical_values": record.values,
            "calculated_values": {
                "population_closing": record.values.get("population_closing"),
                "temporary_closing": record.values.get("temporary_closing"),
            },
            "validation": {
                "status": record.processing_status,
                "valid": not any(
                    issue.get("severity") == IssueSeverity.ERROR.value
                    for issue in validation_messages
                ),
                "messages": validation_messages,
            },
            "source_provenance": record.provenance,
            "sources": [
                item for item in record.records if item.get("record_type") == "population_source"
            ],
            "persisted_report_identifier": record.id,
            "duplicate": duplicate,
            "source_path_preserved": True,
        }
    except (
        PopulationExtractionError,
        PopulationStandardizationError,
        PopulationBundleProcessingError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "issues": [issue.model_dump(mode="json") for issue in exc.issues],
            },
        ) from exc
    except (UnsafeUploadError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        for temporary_path in temporary_paths.values():
            temporary_path.unlink(missing_ok=True)


@router.get("")
def list_operational_reports(
    service: Annotated[OperationalPipelineService, Depends(get_operational_service)],
    domain: Annotated[OperationalDomain | None, Query()] = None,
):
    return {"items": [record_payload(item) for item in service.list(domain)]}


@router.get("/{report_id}")
def get_operational_report(
    report_id: str,
    service: Annotated[OperationalPipelineService, Depends(get_operational_service)],
):
    record = service.get(report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Operational report not found")
    return record_payload(record)


@router.get("/{report_id}/kpis")
def get_operational_kpis(
    report_id: str,
    service: Annotated[OperationalPipelineService, Depends(get_operational_service)],
):
    record = service.get(report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Operational report not found")
    try:
        kpis = calculate_fixture_kpis(
            OperationalDomain(record.domain), record.classification, record.values
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "report_id": report_id,
        "classification": record.classification,
        "definition_label": "SYNTHETIC_NON_PRODUCTION_RULE",
        "kpis": {key: str(value) for key, value in kpis.items()},
    }
