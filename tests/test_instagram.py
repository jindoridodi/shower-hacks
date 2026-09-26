import pytest

from apps.api.config import Settings
from apps.api.schemas.instagram import InstagramProfileRead
from apps.api.services.instagram import (
    ApifyInstagramProfileScraper,
    ApifyNotConfiguredError,
    ApifyProfileError,
)


def test_profile_scraper_normalizes_the_profile_and_recent_captions():
    seen = {}

    def transport(payload):
        seen.update(payload)
        return [
            {
                "username": "example.user",
                "fullName": "Example User",
                "biography": "Coffee and hikes",
                "url": "https://www.instagram.com/example.user/",
                "profilePicUrlHD": "https://images.example/profile.jpg",
                "externalUrl": "https://example.com",
                "businessCategoryName": "Creator",
                "followersCount": 50,
                "followsCount": 20,
                "postsCount": 3,
                "verified": False,
                "private": False,
                "latestPosts": [
                    {
                        "caption": "A recent hike",
                        "url": "https://www.instagram.com/p/one/",
                        "timestamp": "2026-09-01T10:00:00Z",
                        "likesCount": 10,
                        "commentsCount": 2,
                    }
                ],
            }
        ]

    profile = ApifyInstagramProfileScraper(
        Settings(apify_api_token="test-token"), transport=transport
    ).scrape_profile("example.user")

    assert seen == {"usernames": ["example.user"]}
    assert profile.username == "example.user"
    assert profile.is_verified is False
    assert profile.is_private is False
    assert profile.profile_picture_url == "https://images.example/profile.jpg"
    assert profile.recent_posts[0].caption == "A recent hike"


def test_profile_scraper_requires_an_apify_token():
    scraper = ApifyInstagramProfileScraper(Settings(apify_api_token=""))

    with pytest.raises(ApifyNotConfiguredError):
        scraper.scrape_profile("example.user")


def test_profile_scraper_maps_actor_error_rows_to_an_error():
    scraper = ApifyInstagramProfileScraper(
        Settings(apify_api_token="test-token"),
        transport=lambda _: [{"error": "profile_not_found"}],
    )

    with pytest.raises(ApifyProfileError) as caught:
        scraper.scrape_profile("missing")

    assert caught.value.status_code == 404


def test_extract_profile_endpoint_returns_the_normalized_profile(client, monkeypatch):
    profile = InstagramProfileRead(
        username="example.user",
        full_name="Example User",
        biography="Coffee and hikes",
        profile_url="https://www.instagram.com/example.user/",
        profile_picture_url=None,
        external_url=None,
        category=None,
        followers_count=50,
        follows_count=20,
        posts_count=3,
        is_verified=False,
        is_private=False,
        recent_posts=[],
    )

    class Scraper:
        def scrape_profile(self, username):
            assert username == "example.user"
            return profile

    monkeypatch.setattr("apps.api.routes.instagram.get_instagram_profile_scraper", lambda: Scraper())

    response = client.post("/instagram/profiles", json={"username": "example.user"})

    assert response.status_code == 200
    assert response.json()["username"] == "example.user"


def test_extract_profile_endpoint_rejects_invalid_usernames(client):
    response = client.post("/instagram/profiles", json={"username": "@example"})

    assert response.status_code == 422
