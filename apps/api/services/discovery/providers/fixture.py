"""Deterministic discovery provider used for local development and demos."""

from __future__ import annotations

import json
from pathlib import Path

from apps.api.services.discovery.models import ProviderRecord, ProviderResult


def default_fixture_path() -> Path:
    return Path(__file__).resolve().parents[5] / "data" / "fixtures" / "candidates.json"


class FixtureProvider:

    def __init__(self, provider_name: str = "sherlock", fixture_path: Path | None = None) -> None:
        self.name = provider_name
        self.fixture_path = fixture_path or default_fixture_path()

    async def discover(self, query: str) -> ProviderResult:
        try:
            contents = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return ProviderResult(provider=self.name, warnings=["FIXTURE_UNAVAILABLE: candidate fixture is missing"], partial=True)
        except json.JSONDecodeError:
            return ProviderResult(provider=self.name, warnings=["FIXTURE_INVALID: candidate fixture is invalid"], partial=True)
        if not isinstance(contents, dict):
            return ProviderResult(provider=self.name, warnings=["FIXTURE_INVALID: candidate fixture must be an object"], partial=True)

        entries = contents.get(query.casefold(), {}).get(self.name, [])
        if not isinstance(entries, list):
            return ProviderResult(provider=self.name, warnings=["FIXTURE_INVALID: provider fixture must be a list"], partial=True)
        records: list[ProviderRecord] = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            records.append(
                ProviderRecord(
                    url=str(item.get("url", "")),
                    platform=str(item.get("platform", "")) or None,
                    candidate_username=str(item.get("candidateUsername", "")) or None,
                    exact_username_match=True,
                    provider=self.name,
                    match_reason=str(item.get("matchReason", "Fixture candidate with an exact username match.")),
                )
            )
        return ProviderResult(provider=self.name, records=records)
