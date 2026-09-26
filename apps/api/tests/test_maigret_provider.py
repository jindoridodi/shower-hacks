import asyncio
from pathlib import Path

import pytest

from apps.api.services.discovery.models import ProviderError
from apps.api.services.discovery.providers.maigret import MaigretProvider


def test_maigret_parser_keeps_only_claimed_records(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text('{"site_name":"GitHub","url_user":"https://github.com/demo-user","status":"Claimed"}\n{"url_user":"https://example.com/no","status":"Available"}\n')
    records = MaigretProvider()._parse_json(report, "demo-user")
    assert len(records) == 1
    assert records[0].platform == "GitHub"


def test_maigret_missing_binary_is_nonfatal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("apps.api.services.discovery.providers.maigret.shutil.which", lambda _name: None)
    with pytest.raises(ProviderError, match="not installed"):
        asyncio.run(MaigretProvider().discover("demo-user"))
