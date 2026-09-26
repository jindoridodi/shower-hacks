from fastapi import APIRouter, status

from apps.api.errors import APIError
from apps.api.schemas.instagram import InstagramProfileRead, InstagramProfileRequest
from apps.api.services.instagram import (
    ApifyNotConfiguredError,
    ApifyProfileError,
    get_instagram_profile_scraper,
)

router = APIRouter(prefix="/instagram", tags=["instagram"])


@router.post("/profiles", response_model=InstagramProfileRead, status_code=status.HTTP_200_OK)
def extract_profile(payload: InstagramProfileRequest) -> InstagramProfileRead:
    try:
        return get_instagram_profile_scraper().scrape_profile(payload.username)
    except ApifyNotConfiguredError as error:
        raise APIError(503, "apify_not_configured", str(error)) from error
    except ApifyProfileError as error:
        raise APIError(error.status_code, "instagram_profile_unavailable", str(error)) from error
