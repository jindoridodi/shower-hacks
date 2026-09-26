import asyncio

import pytest

from apps.api.services.enrichment.models import SpiderFootStartRequest
from apps.api.services.enrichment.spiderfoot import SpiderFootClient


def test_spiderfoot_rejects_non_local_sidecar() -> None:
    with pytest.raises(ValueError):
        SpiderFootClient(base_url="https://example.com")


def test_spiderfoot_rejects_invalid_modules() -> None:
    with pytest.raises(ValueError):
        SpiderFootStartRequest(target="demo-user", targetType="username", modules=["breach_search"])


def test_spiderfoot_filters_private_urls() -> None:
    client = SpiderFootClient()
    findings = client._findings([["https://example.com/public"], ["https://127.0.0.1/private"]])
    assert [finding.value for finding in findings] == ["https://example.com/public"]
