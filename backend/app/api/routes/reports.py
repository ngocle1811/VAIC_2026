"""Draft generation, artifact download, and human-review APIs."""

from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_session
from app.models.operational_report import OperationalReportRecord
from app.reporting.models import ReportStatus
from app.reporting.repository import GeneratedReportRepository
from app.reporting.service import ReportGenerationService

router = APIRouter(tags=["reports"])


class GenerateReportRequest(BaseModel):
    operational_report_id: str = Field(min_length=1)
    template_id: str = Field(default="synthetic_domain_draft", min_length=1)


class ReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewer: str = Field(min_length=1, max_length=255)
    comment: str | None = Field(default=None, max_length=4000)


def _payload(record):
    return {
        "report_id": record.id,
        "operational_report_id": record.operational_report_id,
        "domain": record.domain,
        "template_id": record.template_id,
        "status": record.status,
        "validation_result": record.validation_result,
        "reviewer_comment": record.reviewer_comment,
        "reviewed_by": record.reviewed_by,
        "created_at": record.created_at,
        "download_url": f"/reports/{record.id}/download",
    }


@router.post("/reports")
def generate_report(
    request: GenerateReportRequest,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    source = session.get(OperationalReportRecord, request.operational_report_id)
    if not source:
        raise HTTPException(status_code=404, detail="Operational report not found")
    try:
        record = ReportGenerationService(
            GeneratedReportRepository(session), settings.report_output_dir
        ).generate(source, request.template_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _payload(record)


@router.get("/reports")
def list_reports(
    session: Annotated[Session, Depends(get_session)],
    report_status: Annotated[ReportStatus | None, Query(alias="status")] = None,
):
    return {
        "items": [_payload(item) for item in GeneratedReportRepository(session).list(report_status)]
    }


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, session: Annotated[Session, Depends(get_session)]):
    record = GeneratedReportRepository(session).get(report_id)
    if not record or not Path(record.artifact_path).is_file():
        raise HTTPException(status_code=404, detail="Report artifact not found")
    return FileResponse(
        record.artifact_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"bao_cao_nhap_{report_id[:8]}.docx",
    )


@router.post("/reviews/{report_id}")
def review_report(
    report_id: str,
    request: ReviewRequest,
    session: Annotated[Session, Depends(get_session)],
):
    repository = GeneratedReportRepository(session)
    record = repository.get(report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        reviewed = repository.review(
            record, ReportStatus(request.decision), request.reviewer, request.comment
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _payload(reviewed)
