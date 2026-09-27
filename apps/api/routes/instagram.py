from fastapi import APIRouter, status

from apps.api.errors import APIError
from apps.api.schemas.instagram import InstagramProfileRead, InstagramProfileRequest
from apps.api.services.instagram import (
    ApifyNotConfiguredError,
    InstagramProfileError,
    get_instagram_profile_scraper,
)

router = APIRouter(prefix="/instagram", tags=["instagram"])


@router.post("/profiles", response_model=InstagramProfileRead, status_code=status.HTTP_200_OK)
def extract_profile(payload: InstagramProfileRequest) -> InstagramProfileRead:
    try:
        return get_instagram_profile_scraper().scrape_profile(payload.username)
    except (ApifyNotConfiguredError, InstagramProfileError) as error:
        raise APIError(error.status_code, error.code, error.message, retryable=error.retryable) from error
