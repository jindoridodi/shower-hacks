"""Provider for URLs explicitly supplied by the user."""

from apps.api.services.discovery.models import ProviderRecord, ProviderResult
from apps.api.services.discovery.normalize import normalize_url, platform_for_url


class ExplicitUrlProvider:
    name = "explicit_url"

    async def discover(self, query: str) -> ProviderResult:
        url = normalize_url(query)
        return ProviderResult(
            provider=self.name,
            records=[
                ProviderRecord(
                    url=url,
                    platform=platform_for_url(url),
                    candidate_username=None,
                    exact_username_match=False,
                    provider=self.name,
                    match_reason="Explicit public URL supplied by the user.",
                    direct_input=True,
                )
            ],
        )
