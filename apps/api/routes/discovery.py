"""HTTP boundary for candidate URL discovery."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.schemas.approval import CandidateApprovalCreate, CandidateApprovalRead
from apps.api.services.approvals import approve_candidate, list_approvals
from apps.api.services.discovery.models import DiscoveryRequest, DiscoveryResponse
from apps.api.services.discovery.service import DiscoveryService
from apps.api.services.manual_sources.repository import ProjectNotFoundError

router = APIRouter(prefix="/api", tags=["discovery"])


@router.post("/discovery", response_model=DiscoveryResponse)
async def discover(request_body: DiscoveryRequest, request: Request) -> DiscoveryResponse:
    service: DiscoveryService = request.app.state.discovery_service
    try:
        return await service.discover(request_body)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/approvals", response_model=CandidateApprovalRead, status_code=status.HTTP_201_CREATED)
def approve(request_body: CandidateApprovalCreate, db: Session = Depends(get_db)) -> CandidateApprovalRead:
    return approve_candidate(db, request_body)


@router.get("/approvals", response_model=list[CandidateApprovalRead])
def list_approved_sources(
    project_id: str = Query(alias="projectId", min_length=1),
    db: Session = Depends(get_db),
) -> list[CandidateApprovalRead]:
    return list_approvals(db, project_id)
