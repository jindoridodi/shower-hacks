"""SQLite engine, migrations, and transaction helper.

Schema changes live in db/migrations. SQLAlchemy models map those tables; the
application does not call metadata.create_all, because FTS5 and triggers are
defined in SQL.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from apps.api.clock import utc_now
from apps.api.config import repo_root
from apps.api.errors import APIError

MIGRATIONS_DIR = repo_root() / "db" / "migrations"


@event.listens_for(Engine, "connect")
def _enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def make_engine(database_path: Path) -> Engine:
    return create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def apply_migrations(database_path: Path) -> list[str]:
    """Apply pending SQL migrations. Running this again is a no-op."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    applied_now: list[str] = []
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
        existing = {
            row[0]
            for row in connection.execute("SELECT version FROM schema_migrations")
        }
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = path.stem
            if version in existing:
                continue
            connection.executescript(path.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, utc_now()),
            )
            connection.commit()
            applied_now.append(version)
    finally:
        connection.close()
    return applied_now


@contextmanager
def transaction(db: Session) -> Iterator[None]:
    try:
        yield
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(
            409,
            "integrity_error",
            "The database rejected this write because a related record is missing "
            "or a unique value already exists.",
        ) from exc
    except OperationalError as exc:
        db.rollback()
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            raise APIError(
                503,
                "database_busy",
                "The database is busy. Retry the request.",
            ) from exc
        raise
    except Exception:
        db.rollback()
        raise
