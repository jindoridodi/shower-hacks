from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.schemas.report import (
    ClaimCreate,
    ClaimRead,
    ClaimSourceCreate,
    ReportCreate,
    ReportRead,
)
from apps.api.services import reports as report_service

router = APIRouter(tags=["reports"])


@router.post("/reports", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, db: Session = Depends(get_db)) -> ReportRead:
    report = report_service.create_report(db, payload.project_id, payload.title)
    return ReportRead.model_validate(report)


@router.get("/reports/{report_id}", response_model=ReportRead)
def get_report(report_id: str, db: Session = Depends(get_db)) -> ReportRead:
    return ReportRead.model_validate(report_service.get_report(db, report_id))


@router.post(
    "/reports/{report_id}/claims",
    response_model=ClaimRead,
    status_code=status.HTTP_201_CREATED,
)
def create_claim(
    report_id: str,
    payload: ClaimCreate,
    db: Session = Depends(get_db),
) -> ClaimRead:
    claim = report_service.create_claim(db, report_id, payload.claim_text, payload.sources)
    return ClaimRead.model_validate(claim)


@router.post(
    "/report-claims/{claim_id}/sources",
    response_model=ClaimRead,
    status_code=status.HTTP_201_CREATED,
)
def add_claim_source(
    claim_id: str,
    payload: ClaimSourceCreate,
    db: Session = Depends(get_db),
) -> ClaimRead:
    claim = report_service.add_claim_source(db, claim_id, payload.source_id, payload.excerpt)
    return ClaimRead.model_validate(claim)
