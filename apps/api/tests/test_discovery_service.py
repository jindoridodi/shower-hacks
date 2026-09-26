import asyncio
from pathlib import Path

from apps.api.services.discovery.models import DiscoveryRequest
from apps.api.services.discovery.providers.explicit_url import ExplicitUrlProvider
from apps.api.services.discovery.providers.fixture import FixtureProvider
from apps.api.services.discovery.service import DiscoveryService


def test_fixture_returns_known_username_and_empty_for_unknown() -> None:
    fixture = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "candidates.json"
    service = DiscoveryService(
        {
            "sherlock": FixtureProvider("sherlock", fixture),
            "maigret": FixtureProvider("maigret", fixture),
            "whatsmyname": FixtureProvider("whatsmyname", fixture),
        },
        use_fixtures=True,
    )
    found = asyncio.run(service.discover(DiscoveryRequest(query="demo-user", queryType="username")))
    missing = asyncio.run(service.discover(DiscoveryRequest(query="nobody", queryType="username")))
    assert found.candidates[0].candidate_username == "demo-user"
    assert found.providers_used == ["sherlock", "maigret", "whatsmyname"]
    assert found.candidates[0].confidence == "high"
    assert missing.candidates == []


def test_explicit_url_returns_high_confidence_candidate() -> None:
    service = DiscoveryService({"explicit_url": ExplicitUrlProvider()})
    response = asyncio.run(service.discover(DiscoveryRequest(query="https://Example.com:443/path/?utm_source=campaign", queryType="url")))
    assert response.candidates[0].url == "https://example.com/path"
    assert response.candidates[0].confidence == "high"
