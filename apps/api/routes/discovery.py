"""HTTP boundary for candidate URL discovery."""

from fastapi import APIRouter, HTTPException, Request, status

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
