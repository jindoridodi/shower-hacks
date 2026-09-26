"""Shared provider protocol."""

from __future__ import annotations

from typing import Protocol

from apps.api.services.discovery.models import ProviderResult


class DiscoveryProvider(Protocol):
    name: str

    async def discover(self, query: str) -> ProviderResult:
        """Return tool-neutral candidates or raise ProviderError."""
