"""Sherlock CLI adapter using its CSV export as the stable machine interface."""

from __future__ import annotations

import asyncio
import csv
import shutil
import tempfile
from pathlib import Path

from apps.api.services.discovery.models import ProviderError, ProviderRecord, ProviderResult

CLAIMED_STATUSES = {"claimed", "querystatus.claimed"}


class SherlockProvider:
    name = "sherlock"

    def __init__(self, site_timeout_seconds: int = 10, process_timeout_seconds: int = 45) -> None:
        self.site_timeout_seconds = site_timeout_seconds
        self.process_timeout_seconds = process_timeout_seconds

    async def discover(self, query: str) -> ProviderResult:
        executable = shutil.which("sherlock")
        if executable is None:
            raise ProviderError("PROVIDER_UNAVAILABLE", "Sherlock is not installed or not on PATH")

        with tempfile.TemporaryDirectory(prefix="borrowed-intimacy-sherlock-") as directory:
            output_directory = Path(directory)
            command = [
                executable,
                "--csv",
                "--folderoutput",
                str(output_directory),
                "--timeout",
                str(self.site_timeout_seconds),
                "--no-color",
                query,
            ]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.process_timeout_seconds)
            except TimeoutError as error:
                process.kill()
                await process.communicate()
                raise ProviderError("PROVIDER_TIMEOUT", "Sherlock did not finish before the process timeout") from error

            csv_path = output_directory / f"{query}.csv"
            if process.returncode != 0:
                detail = stderr.decode("utf-8", errors="replace").strip()
                message = "Sherlock exited without completing discovery"
                if detail:
                    message = f"{message}: {detail[:200]}"
                raise ProviderError("PROVIDER_FAILED", message)
            if not csv_path.exists():
                raise ProviderError("PROVIDER_INVALID_OUTPUT", "Sherlock completed without a CSV result")
            return ProviderResult(provider=self.name, records=self._parse_csv(csv_path, query))

    def _parse_csv(self, csv_path: Path, query: str) -> list[ProviderRecord]:
        records: list[ProviderRecord] = []
        try:
            with csv_path.open(newline="", encoding="utf-8") as file:
                rows = csv.DictReader(file)
                if not rows.fieldnames or not {"name", "url_user", "exists"}.issubset(rows.fieldnames):
                    return []
                for row in rows:
                    if str(row.get("exists", "")).casefold() not in CLAIMED_STATUSES:
                        continue
                    url = str(row.get("url_user", "")).strip()
                    if not url:
                        continue
                    records.append(
                        ProviderRecord(
                            url=url,
                            platform=str(row.get("name", "")).strip() or None,
                            candidate_username=str(row.get("username", query)).strip() or query,
                            exact_username_match=query.casefold() in url.casefold(),
                            provider=self.name,
                            match_reason="Sherlock found a public profile whose URL contains the supplied username.",
                        )
                    )
        except (OSError, csv.Error):
            return []
        return records
