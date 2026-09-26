import asyncio
from pathlib import Path

import pytest

from apps.api.services.discovery.models import ProviderError
from apps.api.services.discovery.providers.sherlock import SherlockProvider


def test_sherlock_csv_parsing_keeps_claimed_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "demo-user.csv"
    csv_path.write_text(
        "username,name,url_main,url_user,exists,http_status,response_time_s\n"
        "demo-user,GitHub,https://github.com,https://github.com/demo-user,Claimed,200,0.1\n"
        "demo-user,Example,https://example.com,https://example.com/demo-user,Available,404,0.1\n",
        encoding="utf-8",
    )
    records = SherlockProvider()._parse_csv(csv_path, "demo-user")
    assert len(records) == 1
    assert records[0].platform == "GitHub"


def test_sherlock_missing_binary_is_nonfatal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("apps.api.services.discovery.providers.sherlock.shutil.which", lambda _name: None)
    with pytest.raises(ProviderError) as error:
        asyncio.run(SherlockProvider().discover("demo-user"))
    assert error.value.code == "PROVIDER_UNAVAILABLE"


def test_sherlock_runs_without_a_shell_and_parses_claimed_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def fake_exec(*command: str, **kwargs: object) -> FakeProcess:
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_directory = Path(command[command.index("--folderoutput") + 1])
        (output_directory / "demo-user.csv").write_text(
            "username,name,url_main,url_user,exists,http_status,response_time_s\n"
            "demo-user,GitHub,https://github.com,https://github.com/demo-user,Claimed,200,0.1\n",
            encoding="utf-8",
        )
        return FakeProcess()

    monkeypatch.setattr("apps.api.services.discovery.providers.sherlock.shutil.which", lambda _name: "/mock/sherlock")
    monkeypatch.setattr("apps.api.services.discovery.providers.sherlock.asyncio.create_subprocess_exec", fake_exec)
    result = asyncio.run(SherlockProvider().discover("demo-user"))

    assert len(result.records) == 1
    assert captured["command"][0] == "/mock/sherlock"
    assert "shell" not in captured["kwargs"]


def test_sherlock_timeout_terminates_process(monkeypatch: pytest.MonkeyPatch) -> None:
    class SlowProcess:
        returncode = None

        def __init__(self) -> None:
            self.killed = False

        def kill(self) -> None:
            self.killed = True

        async def communicate(self) -> tuple[bytes, bytes]:
            if self.killed:
                return b"", b""
            await asyncio.Event().wait()
            return b"", b""

    process = SlowProcess()

    async def fake_exec(*_command: str, **_kwargs: object) -> SlowProcess:
        return process

    monkeypatch.setattr("apps.api.services.discovery.providers.sherlock.shutil.which", lambda _name: "/mock/sherlock")
    monkeypatch.setattr("apps.api.services.discovery.providers.sherlock.asyncio.create_subprocess_exec", fake_exec)

    with pytest.raises(ProviderError) as error:
        asyncio.run(SherlockProvider(process_timeout_seconds=0).discover("demo-user"))

    assert error.value.code == "PROVIDER_TIMEOUT"
    assert process.killed
