import pytest

from apps.api.config import Settings
from apps.api.errors import APIError
from apps.api.services.crawls import ingest_scraped_page
from apps.api.services.firecrawl import (
    FirecrawlPolicyError,
    FirecrawlNotConfiguredError,
    FirecrawlPublicPageScraper,
    ScrapedPage,
    get_public_page_scraper,
)
from tests.helpers import create_project, create_source


def test_scraper_stub_does_not_fetch():
    plain = get_public_page_scraper(
        Settings(database_url="sqlite:///./data/borrowed_intimacy.db", firecrawl_api_key="")
    )
    with pytest.raises(FirecrawlNotConfiguredError):
        plain.scrape_public_url("https://example.com/")

    configured = get_public_page_scraper(
        Settings(
            database_url="sqlite:///./data/borrowed_intimacy.db",
            firecrawl_api_key="test-key",
        )
    )
    with pytest.raises(FirecrawlPolicyError, match="CRAWL_ALLOWED_URLS"):
        configured.scrape_public_url("https://example.com/")


def test_firecrawl_scraper_returns_the_shared_scraped_page_contract():
    seen = {}

    def transport(payload):
        seen.update(payload)
        return {
            "success": True,
            "data": {
                "markdown": "# Public profile",
                "metadata": {"title": "Profile", "sourceURL": "https://example.com/about"},
            },
        }

    scraper = FirecrawlPublicPageScraper(
        Settings(
            firecrawl_api_key="test-key",
            crawl_allowed_urls="https://example.com/about",
            crawl_terms_accepted_hosts="example.com",
        ),
        transport=transport,
        robots_fetcher=lambda _: "User-agent: *\nAllow: /\n",
        host_resolver=lambda _: ["93.184.216.34"],
        sleeper=lambda _: None,
    )

    page = scraper.scrape_public_url("https://example.com/about")

    assert page.markdown == "# Public profile"
    assert page.title == "Profile"
    assert seen == {"url": "https://example.com/about", "formats": ["markdown"], "onlyMainContent": True}


def test_ingest_scraped_page_stores_a_document_and_completes_the_job(client, session):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/about")
    crawl = client.post("/crawls", json={"source_id": source["id"]})
    assert crawl.status_code == 201

    document = ingest_scraped_page(
        session,
        crawl.json()["id"],
        ScrapedPage(url="https://Example.com/about/", markdown="Public bio text", title="About"),
    )
    stored = client.get(f"/documents/{document.id}")
    assert stored.status_code == 200
    assert stored.json()["cleaned_text"] == "Public bio text"
    assert stored.json()["sensitivity_status"] == "unreviewed"
    assert stored.json()["title"] == "About"
    assert stored.json()["content_type"] == "text/markdown"

    refreshed = client.get(f"/crawls/{crawl.json()['id']}").json()
    assert refreshed["status"] == "succeeded"
    assert refreshed["completed_at"]
    source_body = client.get(f"/sources/{source['id']}").json()
    assert source_body["status"] == "succeeded"
    assert source_body["content_hash"] == stored.json()["content_hash"]
    assert source_body["scraped_at"] == refreshed["completed_at"]


def test_ingest_rejects_a_different_url_without_changing_the_job(client, session):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/about")
    crawl = client.post("/crawls", json={"source_id": source["id"]})
    with pytest.raises(APIError) as caught:
        ingest_scraped_page(
            session,
            crawl.json()["id"],
            ScrapedPage(url="https://other.example/page", markdown="Someone else's page"),
        )
    assert caught.value.status_code == 409
    assert caught.value.payload["code"] == "url_mismatch"
    assert client.get(f"/crawls/{crawl.json()['id']}").json()["status"] == "queued"
    assert client.get(f"/sources/{source['id']}").json()["status"] == "queued"
