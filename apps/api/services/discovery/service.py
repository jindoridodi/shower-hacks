"""Provider orchestration and graceful failure handling."""

from __future__ import annotations

import os
from collections.abc import Mapping

from apps.api.services.discovery.models import DiscoveryRequest, DiscoveryResponse, ProviderError, ProviderRecord
from apps.api.services.discovery.normalize import normalize_username
from apps.api.services.discovery.providers.base import DiscoveryProvider
from apps.api.services.discovery.providers.explicit_url import ExplicitUrlProvider
from apps.api.services.discovery.providers.fixture import FixtureProvider
from apps.api.services.discovery.providers.maigret import MaigretProvider
from apps.api.services.discovery.providers.sherlock import SherlockProvider
from apps.api.services.discovery.providers.whatsmyname import WhatsMyNameProvider
from apps.api.services.discovery.scoring import candidates_from_records, provider_evidence_from_records
from apps.api.services.manual_sources.repository import SQLiteSourceRepository


def _enabled(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "true", "yes", "on"}


class DiscoveryService:
    def __init__(
        self,
        providers: Mapping[str, DiscoveryProvider],
        use_fixtures: bool = False,
        source_repository: SQLiteSourceRepository | None = None,
    ) -> None:
        self.providers = dict(providers)
        self.use_fixtures = use_fixtures
        self.source_repository = source_repository

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResponse:
        provider_names = self._provider_names(request)
        records = []
        warnings: list[str] = []
        partial = False
        providers_used: list[str] = []

        for provider_name in provider_names:
            provider = self.providers.get(provider_name)
            if provider is None:
                warnings.append(f"PROVIDER_UNAVAILABLE: {provider_name} is not configured")
                partial = True
                continue
            providers_used.append(provider_name)
            try:
                result = await provider.discover(request.query)
            except ProviderError as error:
                warnings.append(f"{error.code}: {error.message}")
                partial = True
                continue
            records.extend(result.records)
            warnings.extend(result.warnings)
            partial = partial or result.partial

        saved_sources = []
        if request.query_type == "username" and request.project_id and self.source_repository:
            saved_sources = self.source_repository.list_sources(request.project_id, normalize_username(request.query))
            records.extend(
                ProviderRecord(
                    url=source.url,
                    platform=source.platform,
                    candidate_username=source.username,
                    exact_username_match=True,
                    provider="user_supplied",
                    match_reason=source.match_reason,
                    direct_input=True,
                )
                for source in saved_sources
            )

        candidates = candidates_from_records(records, request.limit)
        return DiscoveryResponse(
            query=request.query,
            candidates=candidates,
            providers_used=providers_used,
            provider_evidence=provider_evidence_from_records(records, candidates),
            saved_sources=saved_sources,
            partial=partial,
            warnings=warnings,
        )

    def _provider_names(self, request: DiscoveryRequest) -> list[str]:
        if request.query_type == "url":
            return ["explicit_url"]
        return ["sherlock", "maigret", "whatsmyname"]


def build_default_service(source_repository: SQLiteSourceRepository | None = None) -> DiscoveryService:
    site_timeout = int(os.getenv("SHERLOCK_SITE_TIMEOUT_SECONDS", "10"))
    process_timeout = int(os.getenv("SHERLOCK_PROCESS_TIMEOUT_SECONDS", "45"))
    maigret_site_timeout = int(os.getenv("MAIGRET_SITE_TIMEOUT_SECONDS", "10"))
    maigret_process_timeout = int(os.getenv("MAIGRET_PROCESS_TIMEOUT_SECONDS", "60"))
    maigret_max_sites = int(os.getenv("MAIGRET_MAX_SITES", "500"))
    use_fixtures = _enabled(os.getenv("OSINT_USE_FIXTURES"))
    providers: dict[str, DiscoveryProvider] = {
        "explicit_url": ExplicitUrlProvider(),
        "sherlock": FixtureProvider("sherlock") if use_fixtures else SherlockProvider(site_timeout, process_timeout),
        "maigret": FixtureProvider("maigret") if use_fixtures else MaigretProvider(maigret_site_timeout, maigret_process_timeout, maigret_max_sites),
        "whatsmyname": FixtureProvider("whatsmyname") if use_fixtures else WhatsMyNameProvider.from_environment(),
    }
    return DiscoveryService(providers=providers, use_fixtures=use_fixtures, source_repository=source_repository)
