"""Maigret CLI adapter for confirmed public profile URLs."""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from apps.api.services.discovery.models import ProviderError, ProviderRecord, ProviderResult


class MaigretProvider:
    name = "maigret"

    def __init__(self, site_timeout_seconds: int = 10, process_timeout_seconds: int = 60, max_sites: int = 500) -> None:
        self.site_timeout_seconds = site_timeout_seconds
        self.process_timeout_seconds = process_timeout_seconds
        self.max_sites = max_sites

    async def discover(self, query: str) -> ProviderResult:
        executable = shutil.which("maigret")
        if executable is None:
            raise ProviderError("PROVIDER_UNAVAILABLE", "Maigret is not installed or not on PATH")
        with tempfile.TemporaryDirectory(prefix="borrowed-intimacy-maigret-") as directory:
            output_directory = Path(directory)
            command = [
                executable, query, "--json", "ndjson", "--folderoutput", str(output_directory),
                "--timeout", str(self.site_timeout_seconds), "--top-sites", str(self.max_sites), "--no-progressbar",
            ]
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            try:
                _stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.process_timeout_seconds)
            except TimeoutError as error:
                process.kill()
                await process.communicate()
                raise ProviderError("PROVIDER_TIMEOUT", "Maigret did not finish before the process timeout") from error
            if process.returncode != 0:
                detail = stderr.decode("utf-8", errors="replace").strip()
                message = "Maigret exited without completing discovery"
                raise ProviderError("PROVIDER_FAILED", f"{message}: {detail[:200]}" if detail else message)
            paths = sorted(output_directory.glob("*.json"))
            if not paths:
                raise ProviderError("PROVIDER_INVALID_OUTPUT", "Maigret completed without a JSON result")
            records: list[ProviderRecord] = []
            for path in paths:
                try:
                    records.extend(self._parse_json(path, query))
                except (OSError, json.JSONDecodeError):
                    continue
            if not records and paths:
                # A valid empty report is allowed; malformed reports are not silently treated as matches.
                return ProviderResult(provider=self.name, records=[])
            return ProviderResult(provider=self.name, records=records)

    def _parse_json(self, json_path: Path, query: str) -> list[ProviderRecord]:
        text = json_path.read_text(encoding="utf-8")
        try:
            decoded: Any = json.loads(text)
            entries = self._flatten(decoded)
        except json.JSONDecodeError:
            entries = [json.loads(line) for line in text.splitlines() if line.strip()]
        records: list[ProviderRecord] = []
        for entry in entries:
            if not isinstance(entry, dict) or not self._claimed(entry):
                continue
            url = str(entry.get("url_user") or entry.get("url") or entry.get("profile_url") or "").strip()
            if not url.startswith(("http://", "https://")):
                continue
            records.append(ProviderRecord(
                url=url,
                platform=str(entry.get("site_name") or entry.get("site") or entry.get("name") or "").strip() or None,
                candidate_username=query,
                exact_username_match=query.casefold() in url.casefold(),
                provider=self.name,
                match_reason="Maigret found a public profile for the supplied username.",
            ))
        return records

    @staticmethod
    def _flatten(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            direct = [value] if any(key in value for key in ("url", "url_user", "profile_url")) else []
            nested = [item for item in value.values() if isinstance(item, dict)]
            return direct + nested
        return []

    @staticmethod
    def _claimed(entry: dict[str, Any]) -> bool:
        status = str(entry.get("status") or entry.get("exists") or entry.get("claim") or "").casefold()
        return status in {"claimed", "found", "true", "yes", "querystatus.claimed"}
