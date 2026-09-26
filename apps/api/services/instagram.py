from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from apps.api.config import Settings, get_settings
from apps.api.schemas.instagram import InstagramPostRead, InstagramProfileRead

APIFY_PROFILE_ACTOR = "apify~instagram-profile-scraper"
APIFY_API_URL = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"


class ApifyNotConfiguredError(RuntimeError):
    pass


class ApifyProfileError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApifyInstagramProfileScraper:
    def __init__(
        self,
        settings: Settings,
        transport: Callable[[Mapping[str, object]], list[Mapping[str, object]]] | None = None,
    ) -> None:
        self._token = settings.apify_api_token
        self._transport = transport or self._run_actor

    def scrape_profile(self, username: str) -> InstagramProfileRead:
        if not self._token:
            raise ApifyNotConfiguredError("APIFY_API_TOKEN is not configured.")
        items = self._transport({"usernames": [username]})
        if not items:
            raise ApifyProfileError("Instagram profile was not found", 404)
        item = items[0]
        error = _string(item.get("error")) or _string(item.get("errorMessage"))
        if error:
            raise ApifyProfileError(error, 404 if error in {"not_found", "profile_not_found"} else 502)
        resolved_username = _string(item.get("username"))
        if not resolved_username:
            raise ApifyProfileError("Apify returned a profile without a username")
        posts = item.get("latestPosts") or []
        if not isinstance(posts, list):
            posts = []
        return InstagramProfileRead(
            username=resolved_username,
            full_name=_string(item.get("fullName")),
            biography=_string(item.get("biography")),
            profile_url=_string(item.get("url")),
            profile_picture_url=_string(item.get("profilePicUrlHD")) or _string(item.get("profilePicUrl")),
            external_url=_string(item.get("externalUrl")),
            category=_string(item.get("businessCategoryName")) or _string(item.get("categoryName")),
            followers_count=_integer(item.get("followersCount")),
            follows_count=_integer(item.get("followsCount")),
            posts_count=_integer(item.get("postsCount")),
            is_verified=_boolean(item.get("verified")) if "verified" in item else _boolean(item.get("isVerified")),
            is_private=_boolean(item.get("private")) if "private" in item else _boolean(item.get("isPrivate")),
            recent_posts=[_post(post) for post in posts[:10] if isinstance(post, Mapping) and _string(post.get("caption"))],
        )

    def _run_actor(self, payload: Mapping[str, object]) -> list[Mapping[str, object]]:
        request = Request(
            APIFY_API_URL.format(actor=APIFY_PROFILE_ACTOR),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429 or 500 <= error.code < 600:
                raise ApifyProfileError("Apify is temporarily unavailable", 503) from error
            raise ApifyProfileError("Apify rejected the profile request") from error
        except URLError as error:
            raise ApifyProfileError("Unable to reach Apify", 503) from error
        if not isinstance(body, list) or not all(isinstance(item, Mapping) for item in body):
            raise ApifyProfileError("Apify returned an invalid profile response")
        return body


def get_instagram_profile_scraper(settings: Settings | None = None) -> ApifyInstagramProfileScraper:
    return ApifyInstagramProfileScraper(settings or get_settings())


def _post(item: Mapping[str, object]) -> InstagramPostRead:
    return InstagramPostRead(
        caption=_string(item.get("caption")) or "",
        url=_string(item.get("url")) or _string(item.get("postUrl")),
        timestamp=_string(item.get("timestamp")) or _string(item.get("takenAt")),
        likes_count=_integer(item.get("likesCount")),
        comments_count=_integer(item.get("commentsCount")),
    )


def _string(value: object) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _boolean(value: object) -> bool | None:
    return value if isinstance(value, bool) else None
