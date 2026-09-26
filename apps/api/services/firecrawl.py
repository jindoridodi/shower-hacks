"""Policy-enforced Firecrawl Markdown scraper for the source/crawl schemas."""

from __future__ import annotations

from dataclasses import dataclass
import json
import ipaddress
import ssl
import socket
import time
from typing import Any, Callable, Iterable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

import certifi

from apps.api.config import Settings, get_settings
from apps.api.services.urls import InvalidURL, canonicalize_url


FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape"
USER_AGENT = "BorrowedIntimacyCrawler/0.1"


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


class FirecrawlPolicyError(RuntimeError):
    """Raised when a URL is not approved for public crawling."""


class FirecrawlTransientError(RuntimeError):
    """Raised for retryable Firecrawl or network failures."""


class UnconfiguredFirecrawl:
    def __init__(self, message: str) -> None:
        self._message = message

    def scrape_public_url(self, url: str) -> ScrapedPage:
        raise FirecrawlNotConfiguredError(self._message)


class FirecrawlPublicPageScraper:
    """Fetch one approved public page and return the branch's ``ScrapedPage`` schema."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        robots_fetcher: Callable[[str], str] | None = None,
        host_resolver: Callable[[str], Iterable[str]] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._api_key = settings.firecrawl_api_key
        self._allowed_urls = _csv_urls(settings.crawl_allowed_urls)
        self._terms_hosts = _csv_hosts(settings.crawl_terms_accepted_hosts)
        self._requests_per_minute = settings.crawl_requests_per_minute
        self._transport = transport or self._post_to_firecrawl
        self._robots_fetcher = robots_fetcher or _fetch_robots
        self._host_resolver = host_resolver or _resolve_public_addresses
        self._sleeper = sleeper
        self._clock = clock
        self._last_request_at: float | None = None

    def scrape_public_url(self, url: str) -> ScrapedPage:
        canonical_url = self._assert_allowed(url)
        data = self._scrape_with_retries(canonical_url)
        markdown = data.get("markdown")
        if not isinstance(markdown, str) or not markdown.strip():
            raise FirecrawlNotConfiguredError("Firecrawl returned no Markdown content")
        metadata = data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {}
        title = metadata.get("title") if isinstance(metadata.get("title"), str) else None
        raw_html = data.get("html") if isinstance(data.get("html"), str) else None
        source_url = metadata.get("sourceURL") if isinstance(metadata.get("sourceURL"), str) else canonical_url
        return ScrapedPage(url=source_url, markdown=markdown, title=title, raw_html=raw_html)

    def _assert_allowed(self, url: str) -> str:
        try:
            canonical_url = canonicalize_url(url)
        except InvalidURL as error:
            raise FirecrawlPolicyError(str(error)) from error
        host = urlsplit(canonical_url).hostname or ""
        if canonical_url not in self._allowed_urls:
            raise FirecrawlPolicyError("URL is not in CRAWL_ALLOWED_URLS")
        if not _host_is_approved(host, self._terms_hosts):
            raise FirecrawlPolicyError("Host is not in CRAWL_TERMS_ACCEPTED_HOSTS")
        addresses = tuple(self._host_resolver(host))
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise FirecrawlPolicyError("Host does not resolve to a public address")
        self._assert_robots(canonical_url)
        return canonical_url

    def _assert_robots(self, url: str) -> None:
        parsed = urlsplit(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(self._robots_fetcher(robots_url).splitlines())
        except (HTTPError, URLError, OSError) as error:
            raise FirecrawlPolicyError(f"Unable to verify robots.txt: {error}") from error
        if not parser.can_fetch(USER_AGENT, url):
            raise FirecrawlPolicyError("robots.txt disallows crawling this URL")

    def _scrape_with_retries(self, url: str) -> Mapping[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                self._rate_limit()
                response = self._transport({"url": url, "formats": ["markdown"], "onlyMainContent": True})
                if response.get("success") is False:
                    raise FirecrawlTransientError(str(response.get("error", "Firecrawl scrape failed")))
                data = response.get("data")
                if not isinstance(data, Mapping):
                    raise FirecrawlNotConfiguredError("Firecrawl response did not contain data")
                return data
            except FirecrawlTransientError as error:
                last_error = error
                if attempt == 2:
                    break
                self._sleeper(2**attempt)
        raise FirecrawlNotConfiguredError(f"Firecrawl failed after 3 attempts: {last_error}")

    def _rate_limit(self) -> None:
        if self._requests_per_minute < 1:
            raise FirecrawlPolicyError("CRAWL_REQUESTS_PER_MINUTE must be at least 1")
        now = self._clock()
        if self._last_request_at is not None:
            delay = (60 / self._requests_per_minute) - (now - self._last_request_at)
            if delay > 0:
                self._sleeper(delay)
        self._last_request_at = self._clock()

    def _post_to_firecrawl(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        request = Request(
            FIRECRAWL_SCRAPE_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json", "User-Agent": USER_AGENT},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30, context=_tls_context()) as response:  # nosec B310: fixed Firecrawl endpoint
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429 or 500 <= error.code < 600:
                raise FirecrawlTransientError(f"Firecrawl HTTP {error.code}") from error
            raise FirecrawlNotConfiguredError(f"Firecrawl HTTP {error.code}") from error
        except URLError as error:
            raise FirecrawlTransientError(f"Firecrawl network error: {error.reason}") from error
        if not isinstance(body, Mapping):
            raise FirecrawlNotConfiguredError("Firecrawl returned invalid JSON")
        return body


def get_public_page_scraper(settings: Settings | None = None) -> PublicPageScraper:
    current = settings or get_settings()
    if current.firecrawl_api_key:
        return FirecrawlPublicPageScraper(current)
    return UnconfiguredFirecrawl(
        "FIRECRAWL_API_KEY is not configured."
    )


def _csv_urls(raw: str) -> frozenset[str]:
    return frozenset(canonicalize_url(item) for item in raw.split(",") if item.strip())


def _csv_hosts(raw: str) -> frozenset[str]:
    return frozenset(item.strip().lower().rstrip(".") for item in raw.split(",") if item.strip())


def _allowed_hosts_from_urls(urls: Iterable[str] | str) -> frozenset[str]:
    values = urls.split(",") if isinstance(urls, str) else urls
    hosts: set[str] = set()
    for value in values:
        try:
            host = urlsplit(canonicalize_url(value)).hostname
        except InvalidURL:
            continue
        if host:
            hosts.add(host.lower().rstrip(".").removeprefix("www."))
    return frozenset(hosts)


def _host_is_approved(host: str, approved: Iterable[str]) -> bool:
    lowered = host.lower().rstrip(".")
    return any(lowered == item or lowered.endswith(f".{item}") for item in approved)


def _resolve_public_addresses(host: str) -> Iterable[str]:
    return {item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}


def _fetch_robots(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=10, context=_tls_context()) as response:  # nosec B310: URL is built from a policy-checked URL
        return response.read().decode("utf-8", errors="replace")


def _tls_context() -> ssl.SSLContext:
    """Use certifi so local Python installations verify HTTPS consistently."""
    return ssl.create_default_context(cafile=certifi.where())
