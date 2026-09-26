import pytest

from apps.api.config import Settings
from apps.api.errors import APIError
from apps.api.services.crawls import ingest_scraped_page
from apps.api.services.firecrawl import (
    FirecrawlNotConfiguredError,
    ScrapedPage,
    get_public_page_scraper,
)
from tests.helpers import create_project, create_source


def test_scraper_stub_does_not_fetch():
    plain = get_public_page_scraper(Settings(database_url="sqlite:///./data/borrowed_intimacy.db"))
    with pytest.raises(FirecrawlNotConfiguredError):
        plain.scrape_public_url("https://example.com/")

    configured = get_public_page_scraper(
        Settings(
            database_url="sqlite:///./data/borrowed_intimacy.db",
            firecrawl_api_key="test-key",
        )
    )
    with pytest.raises(FirecrawlNotConfiguredError, match="not implemented"):
        configured.scrape_public_url("https://example.com/")


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
    assert stored.json()["sensitivity_status"] == "clear"
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
