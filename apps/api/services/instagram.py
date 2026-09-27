"""Bounded public-profile lookup through Apify's Instagram Profile Scraper."""

from __future__ import annotations

import json
import socket
import ssl
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import certifi

from apps.api.config import Settings, get_settings
from apps.api.schemas.instagram import InstagramPostRead, InstagramProfileRead

APIFY_API_URL = "https://api.apify.com/v2/actors/{actor}/run-sync-get-dataset-items"
MAX_RECENT_POSTS = 10
_NOT_FOUND_ERRORS = {"not_found", "profile_not_found"}
_UNAVAILABLE_ERRORS = {"collection_failed", "rate_limited", "rate_limit", "temporarily_unavailable"}


class InstagramProfileScraper(Protocol):
    def scrape_profile(self, username: str) -> InstagramProfileRead:
        """Return a normalized profile or raise an InstagramProfileError."""


class InstagramProfileError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable


class ApifyNotConfiguredError(InstagramProfileError):
    def __init__(self) -> None:
        super().__init__(503, "apify_not_configured", "APIFY_API_TOKEN is not configured.", False)


class ApifyProfileError(InstagramProfileError):
    """A stable, client-safe error from the configured profile provider."""


def _error(status_code: int, code: str, message: str, retryable: bool = False) -> ApifyProfileError:
    return ApifyProfileError(status_code, code, message, retryable)


class ApifyInstagramProfileScraper:
    def __init__(
        self,
        settings: Settings,
        transport: Callable[[Mapping[str, object]], list[Mapping[str, object]]] | None = None,
    ) -> None:
        self._token = settings.apify_api_token
        self._actor = settings.apify_instagram_actor
        self._run_timeout_seconds = settings.apify_instagram_timeout_seconds
        self._transport = transport or self._run_actor

    def scrape_profile(self, username: str) -> InstagramProfileRead:
        if not self._token:
            raise ApifyNotConfiguredError()
        if not self._actor.strip() or not 1 <= self._run_timeout_seconds <= 300:
            raise _error(503, "apify_not_configured", "Apify Instagram configuration is invalid.")
        items = self._transport({"usernames": [username], "includeAboutSection": False})
        if not items:
            raise _error(404, "instagram_profile_not_found", "Instagram profile was not found.")
        if len(items) != 1 or not isinstance(items[0], Mapping):
            raise _error(502, "instagram_invalid_response", "Instagram provider returned an invalid profile response.")
        return _normalize_profile(items[0], username)

    def _run_actor(self, payload: Mapping[str, object]) -> list[Mapping[str, object]]:
        actor = quote(self._actor, safe="~")
        query = urlencode({"timeout": self._run_timeout_seconds, "maxItems": 1, "clean": "true"})
        request = Request(
            f"{APIFY_API_URL.format(actor=actor)}?{query}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(
                request,
                timeout=self._run_timeout_seconds + 15,
                context=_tls_context(),
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in {401, 403}:
                raise _error(503, "apify_auth_failed", "Apify authentication was rejected.") from error
            if error.code == 429 or 500 <= error.code < 600:
                raise _error(503, "instagram_provider_unavailable", "Instagram profile provider is temporarily unavailable.", True) from error
            raise _error(502, "instagram_provider_rejected", "Instagram profile provider rejected the request.") from error
        except (URLError, TimeoutError, socket.timeout) as error:
            raise _error(503, "instagram_provider_unavailable", "Instagram profile provider is temporarily unavailable.", True) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _error(502, "instagram_invalid_response", "Instagram provider returned an invalid profile response.") from error
        if not isinstance(body, list) or len(body) != 1 or not isinstance(body[0], Mapping):
            raise _error(502, "instagram_invalid_response", "Instagram provider returned an invalid profile response.")
        return body


class FixtureInstagramProfileScraper:
    """Deterministic local adapter with the same public interface as Apify."""

    def __init__(self, fixture_path: Path | None = None) -> None:
        self._fixture_path = fixture_path or _fixture_path()

    def scrape_profile(self, username: str) -> InstagramProfileRead:
        try:
            fixture = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise _error(503, "instagram_provider_unavailable", "Instagram fixtures are unavailable.", True) from error
        entry = fixture.get(username.casefold()) if isinstance(fixture, Mapping) else None
        if not isinstance(entry, Mapping):
            raise _error(404, "instagram_profile_not_found", "Instagram profile was not found.")
        error_data = entry.get("error")
        if isinstance(error_data, Mapping):
            raise _error(
                int(error_data.get("statusCode", 502)),
                str(error_data.get("code", "instagram_provider_rejected")),
                str(error_data.get("message", "Instagram profile fixture failed.")),
                bool(error_data.get("retryable", False)),
            )
        item = entry.get("item")
        if not isinstance(item, Mapping):
            raise _error(502, "instagram_invalid_response", "Instagram fixture is invalid.")
        return _normalize_profile(item, username)


def get_instagram_profile_scraper(settings: Settings | None = None) -> InstagramProfileScraper:
    current = settings or get_settings()
    if current.instagram_use_fixtures:
        return FixtureInstagramProfileScraper()
    return ApifyInstagramProfileScraper(current)


def _normalize_profile(item: Mapping[str, object], requested_username: str) -> InstagramProfileRead:
    upstream_error = _string(item.get("error")) or _string(item.get("errorMessage"))
    if upstream_error:
        normalized_error = upstream_error.casefold()
        if normalized_error in _NOT_FOUND_ERRORS:
            raise _error(404, "instagram_profile_not_found", "Instagram profile was not found.")
        if normalized_error in _UNAVAILABLE_ERRORS:
            raise _error(503, "instagram_provider_unavailable", "Instagram profile provider is temporarily unavailable.", True)
        raise _error(502, "instagram_provider_rejected", "Instagram profile provider rejected the request.")

    resolved_username = _string(item.get("username"))
    if not resolved_username or not _is_valid_username(resolved_username) or resolved_username.casefold() != requested_username.casefold():
        raise _error(502, "instagram_invalid_response", "Instagram provider returned an invalid profile response.")

    is_private = _boolean(item.get("private")) if "private" in item else _boolean(item.get("isPrivate"))
    is_verified = _boolean(item.get("verified")) if "verified" in item else _boolean(item.get("isVerified"))
    profile = {
        "username": resolved_username,
        "full_name": _string(item.get("fullName")),
        "biography": _string(item.get("biography")),
        "profile_url": f"https://www.instagram.com/{resolved_username}/",
        "profile_picture_url": _string(item.get("profilePicUrlHD")) or _string(item.get("profilePicUrl")),
        "external_url": _string(item.get("externalUrl")),
        "category": _string(item.get("businessCategoryName")) or _string(item.get("categoryName")),
        "followers_count": _integer(item.get("followersCount")),
        "follows_count": _integer(item.get("followsCount")),
        "posts_count": _integer(item.get("postsCount")),
        "is_verified": is_verified,
        "is_private": is_private,
    }
    if is_private is True:
        profile.update(
            full_name=None,
            biography=None,
            profile_picture_url=None,
            external_url=None,
            category=None,
            recent_posts=[],
        )
        return InstagramProfileRead(**profile)

    posts = item.get("latestPosts")
    captioned_posts = [
        _post(post)
        for post in posts
        if isinstance(post, Mapping) and _string(post.get("caption"))
    ] if isinstance(posts, list) else []
    return InstagramProfileRead(**profile, recent_posts=captioned_posts[:MAX_RECENT_POSTS])


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "fixtures" / "instagram-profiles.json"


def _tls_context() -> ssl.SSLContext:
    """Use certifi so local Python installations verify HTTPS consistently."""
    return ssl.create_default_context(cafile=certifi.where())


def _post(item: Mapping[str, object]) -> InstagramPostRead:
    return InstagramPostRead(
        caption=_string(item.get("caption")) or "",
        url=_string(item.get("url")) or _string(item.get("postUrl")),
        timestamp=_string(item.get("timestamp")) or _string(item.get("takenAt")),
        likes_count=_integer(item.get("likesCount")),
        comments_count=_integer(item.get("commentsCount")),
    )


def _is_valid_username(value: str) -> bool:
    return 1 <= len(value) <= 30 and all(character.isalnum() or character in "._" for character in value)


def _string(value: object) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _boolean(value: object) -> bool | None:
    return value if isinstance(value, bool) else None
