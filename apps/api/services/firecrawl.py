"""Public-page scraper seam.

Emily's Firecrawl client should implement PublicPageScraper.scrape_public_url.
A worker can then pass the ScrapedPage to apps.api.services.crawls.ingest_scraped_page.

This module does not call the network. The method accepts only a URL so the
client has no parameter for cookies, session tokens, or access-control bypasses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from apps.api.config import Settings, get_settings


@dataclass(frozen=True)
class ScrapedPage:
    url: str
    markdown: str
    title: str | None = None
    raw_html: str | None = None


class PublicPageScraper(Protocol):
    def scrape_public_url(self, url: str) -> ScrapedPage:
        """Fetch one publicly accessible page."""


class FirecrawlNotConfiguredError(RuntimeError):
    """Raised when scrape is called before a Firecrawl client is installed."""


class UnconfiguredFirecrawl:
    def __init__(self, message: str) -> None:
        self._message = message

    def scrape_public_url(self, url: str) -> ScrapedPage:
        raise FirecrawlNotConfiguredError(self._message)


def get_public_page_scraper(settings: Settings | None = None) -> PublicPageScraper:
    current = settings or get_settings()
    if current.firecrawl_api_key:
        return UnconfiguredFirecrawl(
            "FIRECRAWL_API_KEY is set, but the Firecrawl client is not implemented yet."
        )
    return UnconfiguredFirecrawl(
        "No public-page scraper is configured. Implement PublicPageScraper "
        "and pass scraped pages to ingest_scraped_page."
    )
