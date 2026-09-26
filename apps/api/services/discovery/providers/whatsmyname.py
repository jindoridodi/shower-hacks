"""GET-only WhatsMyName data-set adapter for public profile patterns."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import socket
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from apps.api.services.discovery.models import ProviderError, ProviderRecord, ProviderResult
from apps.api.services.discovery.normalize import validate_public_url


def _cache_path() -> Path:
    return Path(__file__).resolve().parents[5] / "data" / "cache" / "whatsmyname-data.json"


class WhatsMyNameProvider:
    name = "whatsmyname"

    def __init__(self, data_url: str, cache_path: Path | None = None, cache_ttl_seconds: int = 86400,
                 site_timeout_seconds: int = 8, max_concurrency: int = 20) -> None:
        self.data_url = data_url
        self.cache_path = cache_path or _cache_path()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.site_timeout_seconds = site_timeout_seconds
        self.max_concurrency = max_concurrency

    @classmethod
    def from_environment(cls) -> "WhatsMyNameProvider":
        return cls(
            os.getenv("WHATS_MY_NAME_DATA_URL", "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"),
            cache_ttl_seconds=int(os.getenv("WHATS_MY_NAME_CACHE_TTL_SECONDS", "86400")),
            site_timeout_seconds=int(os.getenv("WHATS_MY_NAME_SITE_TIMEOUT_SECONDS", "8")),
            max_concurrency=int(os.getenv("WHATS_MY_NAME_MAX_CONCURRENCY", "20")),
        )

    async def discover(self, query: str) -> ProviderResult:
        data, warnings = await self._load_data()
        sites = data.get("sites", [])
        semaphore = asyncio.Semaphore(self.max_concurrency)
        timeout = httpx.Timeout(self.site_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": "BorrowedIntimacy/0.1"}) as client:
            checks = [self._check_site(client, semaphore, site, query) for site in sites if self._is_get_compatible(site)]
            checked = await asyncio.gather(*checks, return_exceptions=True)
        records = [item for item in checked if isinstance(item, ProviderRecord)]
        failures = sum(isinstance(item, Exception) for item in checked)
        if failures:
            warnings.append(f"PROVIDER_PARTIAL: WhatsMyName skipped {failures} unreachable site checks")
        return ProviderResult(provider=self.name, records=records, warnings=warnings, partial=bool(failures))

    async def _load_data(self) -> tuple[dict[str, Any], list[str]]:
        cached = self._read_cache()
        fresh = cached is not None and time.time() - self.cache_path.stat().st_mtime < self.cache_ttl_seconds
        if fresh:
            return cached, []
        try:
            validate_public_url(self.data_url)
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.site_timeout_seconds), follow_redirects=True) as client:
                response = await client.get(self.data_url)
                response.raise_for_status()
            payload = response.json()
            self._validate_dataset(payload)
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload, []
        except (httpx.HTTPError, OSError, ValueError, json.JSONDecodeError):
            if cached is not None:
                return cached, ["PROVIDER_STALE_CACHE: WhatsMyName dataset refresh failed; using cached data"]
            raise ProviderError("PROVIDER_UNAVAILABLE", "WhatsMyName dataset could not be loaded")

    def _read_cache(self) -> dict[str, Any] | None:
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            self._validate_dataset(payload)
            return payload
        except (OSError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _validate_dataset(payload: Any) -> None:
        if not isinstance(payload, dict) or not isinstance(payload.get("sites"), list):
            raise ValueError("invalid WhatsMyName dataset")

    @staticmethod
    def _is_get_compatible(site: Any) -> bool:
        return (
            isinstance(site, dict) and site.get("valid", True) is not False and not site.get("post_body")
            and not site.get("headers") and isinstance(site.get("uri_check"), str)
            and "{account}" in site["uri_check"] and site.get("cat") != "xx NSFW xx"
        )

    async def _check_site(self, client: httpx.AsyncClient, semaphore: asyncio.Semaphore, site: dict[str, Any], query: str) -> ProviderRecord | None:
        target = site["uri_check"].replace("{account}", quote(query, safe="._-"))
        if not await self._is_public_http_target(target):
            return None
        async with semaphore:
            response = await client.get(target)
        body = response.text[:1_000_000]
        exists_code = site.get("e_code")
        exists_string = str(site.get("e_string") or "")
        missing_code = site.get("m_code")
        missing_string = str(site.get("m_string") or "")
        exists = (exists_code is not None and response.status_code == exists_code) or (exists_string and exists_string in body)
        missing = (missing_code is not None and response.status_code == missing_code) or (missing_string and missing_string in body)
        if not exists or missing:
            return None
        url = str(site.get("uri_pretty") or site["uri_check"]).replace("{account}", quote(query, safe="._-"))
        return ProviderRecord(url, str(site.get("name") or "") or None, query, query.casefold() in url.casefold(), self.name,
                              "WhatsMyName matched a public profile pattern for the supplied username.")

    @staticmethod
    async def _is_public_http_target(value: str) -> bool:
        try:
            validate_public_url(value)
            hostname = urlparse(value).hostname
            if not hostname:
                return False
            addresses = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
            for address in addresses:
                ip = ipaddress.ip_address(address[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
                    return False
            return True
        except (OSError, ValueError):
            return False
