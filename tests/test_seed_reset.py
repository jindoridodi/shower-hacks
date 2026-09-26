import os
import subprocess
import sys
from pathlib import Path

import pytest

from sqlalchemy import func, select, text

from apps.api.config import repo_root
from apps.api.db import make_engine, make_session_factory
from apps.api.errors import ResetRefused
from apps.api.models import Project
from apps.api.reset import reset_local_database
from apps.api.seed import seed_demo

ROOT = repo_root()


def test_seed_is_idempotent_and_reset_clears_only_the_dev_database(tmp_path):
    url = "sqlite:///./data/borrowed_intimacy.db"
    path = reset_local_database(database_url=url, root=tmp_path)
    assert path == Path(os.path.normpath(tmp_path / "data" / "borrowed_intimacy.db"))
    assert path.is_file()

    engine = make_engine(path)
    session = make_session_factory(engine)()
    try:
        first = seed_demo(session)
        second = seed_demo(session)
        assert first.created is True
        assert second.created is False
        assert first.project.id == second.project.id
        assert first.source.id == second.source.id
        assert first.source.canonical_url == "https://example.com/"
        assert first.source.url == "https://example.com/"
        assert session.scalar(select(func.count()).select_from(Project)) == 1
    finally:
        session.close()
        engine.dispose()

    reset_local_database(database_url=url, root=tmp_path)
    reopened = make_engine(path)
    check = make_session_factory(reopened)()
    try:
        assert check.scalar(select(func.count()).select_from(Project)) == 0
        versions = check.execute(text("SELECT version FROM schema_migrations")).scalars().all()
        assert versions == ["001_initial", "002_raw_document_contract", "002_uniqueness", "003_document_processing"]
    finally:
        check.close()
        reopened.dispose()


def test_reset_refuses_other_database_targets(tmp_path):
    with pytest.raises(ResetRefused):
        reset_local_database(database_url="sqlite:///./data/other.db", root=tmp_path)
    assert not (tmp_path / "data" / "other.db").exists()

    outside = tmp_path / "secret.db"
    outside.write_text("keep", encoding="utf-8")
    with pytest.raises(ResetRefused):
        reset_local_database(database_url=f"sqlite:///{outside}", root=tmp_path)
    assert outside.read_text(encoding="utf-8") == "keep"

    with pytest.raises(ResetRefused):
        reset_local_database(
            database_url="postgresql://localhost/borrowed_intimacy",
            root=tmp_path,
        )


def test_migrate_and_seed_scripts(tmp_path):
    database_path = tmp_path / "cli.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path}"

    first = _run("scripts/migrate.py", env)
    assert first.returncode == 0, first.stderr
    assert "Applied: 001_initial" in first.stdout

    second = _run("scripts/migrate.py", env)
    assert second.returncode == 0, second.stderr
    assert "Migrations already current" in second.stdout

    seeded = _run("scripts/seed.py", env)
    assert seeded.returncode == 0, seeded.stderr
    assert "canonical_url=https://example.com/" in seeded.stdout
    assert "created=yes" in seeded.stdout

    again = _run("scripts/seed.py", env)
    assert again.returncode == 0, again.stderr
    assert "created=no" in again.stdout


def test_reset_cli_refuses_a_database_outside_the_dev_path(tmp_path):
    target = tmp_path / "secret.db"
    target.write_bytes(b"keep")
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{target}"
    result = _run("scripts/reset_db.py", env)
    assert result.returncode != 0
    assert target.read_bytes() == b"keep"


def _run(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
