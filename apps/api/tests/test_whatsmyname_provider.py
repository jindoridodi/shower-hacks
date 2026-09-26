import asyncio
import json
from pathlib import Path

from apps.api.services.discovery.providers.whatsmyname import WhatsMyNameProvider


def test_whatsmyname_fixture_cache_is_loaded_without_network(tmp_path: Path) -> None:
    cache = tmp_path / "wmn.json"
    cache.write_text(json.dumps({"sites": []}))
    provider = WhatsMyNameProvider("https://example.com/wmn.json", cache_path=cache)
    data, warnings = asyncio.run(provider._load_data())
    assert data == {"sites": []}
    assert warnings == []


def test_whatsmyname_only_allows_get_compatible_sites() -> None:
    assert WhatsMyNameProvider._is_get_compatible({"uri_check": "https://example.com/{account}", "cat": "social"})
    assert not WhatsMyNameProvider._is_get_compatible({"uri_check": "https://example.com/{account}", "post_body": "{}"})
    assert not WhatsMyNameProvider._is_get_compatible({"uri_check": "https://example.com/{account}", "headers": {"X": "1"}})
