"""Explicit selected-source SpiderFoot enrichment routes."""

from fastapi import APIRouter, HTTPException

from apps.api.services.enrichment.models import SpiderFootStartRequest, SpiderFootStartResponse, SpiderFootStatusResponse
from apps.api.services.enrichment.spiderfoot import SpiderFootClient

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


@router.post("/spiderfoot", response_model=SpiderFootStartResponse)
async def start_spiderfoot(request: SpiderFootStartRequest) -> SpiderFootStartResponse:
    try:
        return await SpiderFootClient().start(request)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/spiderfoot/{job_id}", response_model=SpiderFootStatusResponse)
async def spiderfoot_status(job_id: str, target: str = "") -> SpiderFootStatusResponse:
    try:
        return await SpiderFootClient().status(job_id, target)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
