import json
import socket
from urllib.error import HTTPError, URLError

import pytest

from apps.api.config import Settings
from apps.api.schemas.instagram import InstagramProfileRead
from apps.api.services.instagram import (
    ApifyInstagramProfileScraper,
    ApifyNotConfiguredError,
    FixtureInstagramProfileScraper,
    InstagramProfileError,
    get_instagram_profile_scraper,
)


def _public_item(**overrides):
    item = {
        "username": "example.user",
        "fullName": "Example User",
        "biography": "Coffee and hikes",
        "url": "https://untrusted.example/profile",
        "profilePicUrlHD": "https://images.example/profile.jpg",
        "externalUrl": "https://example.com",
        "businessCategoryName": "Creator",
        "followersCount": 50,
        "followsCount": 20,
        "postsCount": 3,
        "verified": False,
        "private": False,
        "latestPosts": [{"caption": "A recent hike", "url": "https://www.instagram.com/p/one/", "likesCount": 10, "commentsCount": 2}],
    }
    item.update(overrides)
    return item


def _scraper(transport):
    return ApifyInstagramProfileScraper(Settings(apify_api_token="test-token"), transport=transport)


def test_profile_scraper_normalizes_public_profile_and_captioned_posts():
    seen = {}

    def transport(payload):
        seen.update(payload)
        return [_public_item(latestPosts=[{"caption": ""}, {"caption": "First"}, {"caption": "Second"}])]

    profile = _scraper(transport).scrape_profile("example.user")

    assert seen == {"usernames": ["example.user"], "includeAboutSection": False}
    assert profile.profile_url == "https://www.instagram.com/example.user/"
    assert [post.caption for post in profile.recent_posts] == ["First", "Second"]
    assert profile.profile_picture_url == "https://images.example/profile.jpg"


def test_profile_scraper_limits_captioned_posts_and_ignores_invalid_counts():
    posts = [{"caption": f"Post {index}"} for index in range(12)]
    profile = _scraper(lambda _: [_public_item(followersCount="50", latestPosts=posts)]).scrape_profile("example.user")

    assert len(profile.recent_posts) == 10
    assert profile.recent_posts[-1].caption == "Post 9"
    assert profile.followers_count is None


def test_private_profiles_are_metadata_only():
    profile = _scraper(lambda _: [_public_item(private=True, verified=True, latestPosts=[{"caption": "hidden"}])]).scrape_profile("example.user")

    assert profile.is_private is True
    assert profile.is_verified is True
    assert profile.followers_count == 50
    assert profile.full_name is None
    assert profile.biography is None
    assert profile.profile_picture_url is None
    assert profile.external_url is None
    assert profile.category is None
    assert profile.recent_posts == []


def test_profile_scraper_requires_an_apify_token():
    with pytest.raises(ApifyNotConfiguredError) as caught:
        ApifyInstagramProfileScraper(Settings(apify_api_token="")).scrape_profile("example.user")

    assert caught.value.code == "apify_not_configured"
    assert caught.value.retryable is False


@pytest.mark.parametrize(
    ("item", "code", "status"),
    [
        ({"error": "profile_not_found"}, "instagram_profile_not_found", 404),
        ({"error": "rate_limited"}, "instagram_provider_unavailable", 503),
        ({"error": "other_error"}, "instagram_provider_rejected", 502),
        ({"username": "other.user"}, "instagram_invalid_response", 502),
        ({"username": "bad user"}, "instagram_invalid_response", 502),
    ],
)
def test_profile_scraper_maps_upstream_rows_to_stable_errors(item, code, status):
    with pytest.raises(InstagramProfileError) as caught:
        _scraper(lambda _: [item]).scrape_profile("example.user")

    assert caught.value.code == code
    assert caught.value.status_code == status


def test_profile_scraper_rejects_empty_or_malformed_upstream_results():
    for transport in (lambda _: [], lambda _: [{}, {}], lambda _: [{}]):
        with pytest.raises(InstagramProfileError) as caught:
            _scraper(transport).scrape_profile("example.user")
        assert caught.value.code in {"instagram_profile_not_found", "instagram_invalid_response"}


def test_apify_request_uses_bearer_header_and_no_token_in_url(monkeypatch):
    captured = {"calls": 0}

    class Response:
        def read(self):
            return json.dumps([_public_item()]).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout, context):
        captured["calls"] += 1
        captured["request"] = request
        captured["timeout"] = timeout
        captured["context"] = context
        return Response()

    monkeypatch.setattr("apps.api.services.instagram.urlopen", fake_urlopen)
    profile = ApifyInstagramProfileScraper(Settings(apify_api_token="secret-token")).scrape_profile("example.user")

    assert profile.username == "example.user"
    assert profile.profile_picture_url == "https://images.example/profile.jpg"
    assert captured["calls"] == 1
    assert captured["request"].get_header("Authorization") == "Bearer secret-token"
    assert "secret-token" not in captured["request"].full_url
    assert "maxItems=1" in captured["request"].full_url
    assert "clean=true" in captured["request"].full_url
    assert captured["timeout"] == 105


def test_apify_invalid_json_is_a_non_retryable_response_error(monkeypatch):
    class Response:
        def read(self):
            return b"not json"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("apps.api.services.instagram.urlopen", lambda *_args, **_kwargs: Response())
    with pytest.raises(InstagramProfileError) as caught:
        ApifyInstagramProfileScraper(Settings(apify_api_token="secret-token")).scrape_profile("example.user")

    assert caught.value.code == "instagram_invalid_response"
    assert caught.value.retryable is False


@pytest.mark.parametrize(
    ("error", "code", "status", "retryable"),
    [
        (HTTPError("https://api.apify.com", 401, "", None, None), "apify_auth_failed", 503, False),
        (HTTPError("https://api.apify.com", 429, "", None, None), "instagram_provider_unavailable", 503, True),
        (HTTPError("https://api.apify.com", 500, "", None, None), "instagram_provider_unavailable", 503, True),
        (HTTPError("https://api.apify.com", 400, "", None, None), "instagram_provider_rejected", 502, False),
        (URLError("offline"), "instagram_provider_unavailable", 503, True),
        (socket.timeout(), "instagram_provider_unavailable", 503, True),
    ],
)
def test_apify_http_and_network_failures_are_stable(monkeypatch, error, code, status, retryable):
    def fake_urlopen(*_args, **_kwargs):
        raise error

    monkeypatch.setattr("apps.api.services.instagram.urlopen", fake_urlopen)
    with pytest.raises(InstagramProfileError) as caught:
        ApifyInstagramProfileScraper(Settings(apify_api_token="secret-token")).scrape_profile("example.user")

    assert caught.value.code == code
    assert caught.value.status_code == status
    assert caught.value.retryable is retryable
    assert "secret-token" not in caught.value.message


def test_fixtures_cover_public_private_not_found_and_unavailable():
    scraper = FixtureInstagramProfileScraper()
    public = scraper.scrape_profile("demo.public")
    private = scraper.scrape_profile("demo.private")

    assert len(public.recent_posts) == 10
    assert private.is_private is True
    assert private.recent_posts == []
    for username, code in (("demo.missing", "instagram_profile_not_found"), ("demo.unavailable", "instagram_provider_unavailable")):
        with pytest.raises(InstagramProfileError) as caught:
            scraper.scrape_profile(username)
        assert caught.value.code == code


def test_fixture_setting_selects_the_fixture_adapter_without_a_token():
    scraper = get_instagram_profile_scraper(Settings(instagram_use_fixtures=True))
    assert isinstance(scraper, FixtureInstagramProfileScraper)
    assert scraper.scrape_profile("demo.public").username == "demo.public"


def test_extract_profile_endpoint_returns_normalized_profile(client, monkeypatch):
    profile = InstagramProfileRead(
        username="example.user", full_name="Example User", biography="Coffee and hikes",
        profile_url="https://www.instagram.com/example.user/", profile_picture_url=None,
        external_url=None, category=None, followers_count=50, follows_count=20, posts_count=3,
        is_verified=False, is_private=False, recent_posts=[],
    )
    monkeypatch.setattr("apps.api.routes.instagram.get_instagram_profile_scraper", lambda: _StaticScraper(profile))

    response = client.post("/instagram/profiles", json={"username": "example.user"})

    assert response.status_code == 200
    assert response.json()["username"] == "example.user"


@pytest.mark.parametrize(
    ("username", "status", "code"),
    [
        ("demo.public", 200, None),
        ("demo.private", 200, None),
        ("demo.missing", 404, "instagram_profile_not_found"),
        ("demo.unavailable", 503, "instagram_provider_unavailable"),
    ],
)
def test_extract_profile_endpoint_exposes_fixture_states(client, monkeypatch, username, status, code):
    monkeypatch.setattr("apps.api.routes.instagram.get_instagram_profile_scraper", FixtureInstagramProfileScraper)
    response = client.post("/instagram/profiles", json={"username": username})

    assert response.status_code == status
    if status == 200:
        assert response.json()["username"] == username
    else:
        assert response.json()["detail"]["code"] == code


@pytest.mark.parametrize(
    ("error", "status", "code", "retryable"),
    [
        (ApifyNotConfiguredError(), 503, "apify_not_configured", False),
        (InstagramProfileError(404, "instagram_profile_not_found", "not found", False), 404, "instagram_profile_not_found", False),
        (InstagramProfileError(503, "instagram_provider_unavailable", "unavailable", True), 503, "instagram_provider_unavailable", True),
    ],
)
def test_extract_profile_endpoint_returns_stable_errors(client, monkeypatch, error, status, code, retryable):
    monkeypatch.setattr("apps.api.routes.instagram.get_instagram_profile_scraper", lambda: _RaisingScraper(error))

    response = client.post("/instagram/profiles", json={"username": "example.user"})

    assert response.status_code == status
    assert response.json()["detail"] == {"code": code, "message": str(error), "retryable": retryable}


def test_extract_profile_endpoint_rejects_invalid_usernames(client):
    response = client.post("/instagram/profiles", json={"username": "@example"})
    assert response.status_code == 422


class _StaticScraper:
    def __init__(self, profile):
        self.profile = profile

    def scrape_profile(self, username):
        assert username == "example.user"
        return self.profile


class _RaisingScraper:
    def __init__(self, error):
        self.error = error

    def scrape_profile(self, _username):
        raise self.error
