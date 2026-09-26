"""Reset helper for the local development database.

The CLI deletes only data/borrowed_intimacy.db inside the project root, then
reapplies migrations. Any other DATABASE_URL is refused.
"""

from __future__ import annotations

import os
from pathlib import Path

from apps.api.config import DEV_DATABASE_FILENAME, database_path_from_url, get_settings, repo_root
from apps.api.db import apply_migrations
from apps.api.errors import ResetRefused


def reset_local_database(
    *,
    database_url: str | None = None,
    root: Path | None = None,
) -> Path:
    base = root or repo_root()
    url = database_url if database_url is not None else get_settings().database_url
    if not url.startswith("sqlite:"):
        raise ResetRefused("Reset only deletes the local SQLite development database.")
    try:
        path = database_path_from_url(url, base)
    except ValueError as exc:
        raise ResetRefused(str(exc)) from exc

    data_dir = Path(os.path.normpath(base / "data"))
    if path.parent != data_dir or path.name != DEV_DATABASE_FILENAME:
        raise ResetRefused(
            "Reset only deletes data/borrowed_intimacy.db inside the project root. "
            f"Refusing {path}."
        )

    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if candidate.is_file() or candidate.is_symlink():
            candidate.unlink()
    apply_migrations(path)
    return path
