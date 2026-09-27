from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.errors import APIError
from apps.api.schemas.instagram import (
    InstagramProfileIngestRead,
    InstagramProfileRead,
    InstagramProfileRequest,
)
from apps.api.services.instagram import (
    ApifyNotConfiguredError,
    ApifyProfileError,
    InstagramProfileError,
    get_instagram_profile_scraper,
    ingest_profile,
)

router = APIRouter(prefix="/instagram", tags=["instagram"])


@router.post("/profiles", response_model=InstagramProfileRead, status_code=status.HTTP_200_OK)
def extract_profile(payload: InstagramProfileRequest) -> InstagramProfileRead:
    try:
        return get_instagram_profile_scraper().scrape_profile(payload.username)
    except (ApifyNotConfiguredError, InstagramProfileError) as error:
        raise APIError(error.status_code, error.code, error.message, retryable=error.retryable) from error


@router.post(
    "/projects/{project_id}/profiles",
    response_model=InstagramProfileIngestRead,
    status_code=status.HTTP_201_CREATED,
)
def ingest_profile_for_project(
    project_id: str,
    payload: InstagramProfileRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> InstagramProfileIngestRead:
    try:
        profile, source, document, deduplicated, chunk_count = ingest_profile(
            db,
            project_id=project_id,
            username=payload.username,
            scraper=get_instagram_profile_scraper(),
        )
    except ApifyNotConfiguredError as error:
        raise APIError(503, "apify_not_configured", str(error)) from error
    except ApifyProfileError as error:
        raise APIError(error.status_code, "instagram_profile_unavailable", str(error)) from error
    response.status_code = status.HTTP_200_OK if deduplicated else status.HTTP_201_CREATED
    return InstagramProfileIngestRead(
        profile=profile,
        source_id=source.id,
        document_id=document.id,
        document_deduplicated=deduplicated,
        chunk_count=chunk_count,
    )
