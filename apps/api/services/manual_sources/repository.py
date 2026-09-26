"""Small SQLite repository for projects and selected public source URLs."""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from apps.api.services.discovery.models import SavedSource
from apps.api.services.discovery.normalize import normalize_url, platform_for_url
from apps.api.services.manual_sources.models import Project


class ProjectNotFoundError(LookupError):
    pass


class SourceNotFoundError(LookupError):
    pass


class DuplicateSourceError(ValueError):
    pass


def database_path_from_environment() -> str:
    # Keep OSINT manual-source storage off the main migrated database.
    database_url = os.getenv("OSINT_DATABASE_URL", "sqlite:///./data/osint_sources.db")
    if not database_url.startswith("sqlite:///"):
        raise ValueError("OSINT_DATABASE_URL must use sqlite:///...")
    return database_url.removeprefix("sqlite:///")


class SQLiteSourceRepository:
    def __init__(self, database_path: str | None = None) -> None:
        self.database_path = database_path or database_path_from_environment()
        self._memory_connection: sqlite3.Connection | None = None
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        if self.database_path == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_connection.row_factory = sqlite3.Row
            return self._memory_connection
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    target_username TEXT NOT NULL,
                    url TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    UNIQUE (project_id, target_username, canonical_url)
                );
                """
            )
            self._migrate_sources_table(connection)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS sources_project_username_idx ON sources (project_id, target_username)"
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS user_supplied_source_identity_unique
                ON sources (project_id, target_username, canonical_url)
                WHERE source_type = 'user_supplied'
                """
            )
            connection.commit()
        finally:
            if connection is not self._memory_connection:
                connection.close()

    @staticmethod
    def _migrate_sources_table(connection: sqlite3.Connection) -> None:
        """Bring an earlier planned `sources` table up to the selected-source contract."""

        columns = {row["name"] for row in connection.execute("PRAGMA table_info(sources)")}
        additions = {
            "target_username": "TEXT NOT NULL DEFAULT ''",
            "canonical_url": "TEXT NOT NULL DEFAULT ''",
            "source_type": "TEXT NOT NULL DEFAULT 'unknown'",
            "status": "TEXT NOT NULL DEFAULT 'pending'",
            "created_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in additions.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE sources ADD COLUMN {column} {definition}")

    def create_project(self, name: str) -> Project:
        project = Project(projectId=str(uuid.uuid4()), name=name, createdAt=_now())
        self._execute(
            "INSERT INTO projects (id, name, created_at) VALUES (?, ?, ?)",
            (project.project_id, project.name, project.created_at),
        )
        return project

    def list_projects(self) -> list[Project]:
        rows = self._fetchall("SELECT id, name, created_at FROM projects ORDER BY created_at, id")
        return [Project(projectId=row["id"], name=row["name"], createdAt=row["created_at"]) for row in rows]

    def project_exists(self, project_id: str) -> bool:
        return self._fetchone("SELECT 1 FROM projects WHERE id = ?", (project_id,)) is not None

    def add_source(self, project_id: str, username: str, url: str) -> SavedSource:
        self._require_project(project_id)
        canonical_url = normalize_url(url)
        source = SavedSource(
            sourceId=str(uuid.uuid4()),
            projectId=project_id,
            username=username,
            url=canonical_url,
            platform=platform_for_url(canonical_url),
            createdAt=_now(),
        )
        try:
            self._execute(
                """
                INSERT INTO sources
                    (id, project_id, target_username, url, canonical_url, source_type, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'user_supplied', 'selected', ?)
                """,
                (source.source_id, project_id, username, canonical_url, canonical_url, source.created_at),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateSourceError("This URL is already attached to this project and username") from error
        return source

    def list_sources(self, project_id: str, username: str) -> list[SavedSource]:
        self._require_project(project_id)
        rows = self._fetchall(
            """
            SELECT id, project_id, target_username, canonical_url, created_at
            FROM sources
            WHERE project_id = ? AND target_username = ? AND source_type = 'user_supplied'
            ORDER BY created_at, id
            """,
            (project_id, username),
        )
        return [self._source_from_row(row) for row in rows]

    def delete_source(self, project_id: str, source_id: str) -> None:
        self._require_project(project_id)
        connection = self._connect()
        try:
            cursor = connection.execute("DELETE FROM sources WHERE id = ? AND project_id = ?", (source_id, project_id))
            connection.commit()
            if cursor.rowcount != 1:
                raise SourceNotFoundError("Saved source was not found")
        finally:
            if connection is not self._memory_connection:
                connection.close()

    def _source_from_row(self, row: sqlite3.Row) -> SavedSource:
        url = row["canonical_url"]
        return SavedSource(
            sourceId=row["id"], projectId=row["project_id"], username=row["target_username"],
            url=url, platform=platform_for_url(url), createdAt=row["created_at"],
        )

    def _require_project(self, project_id: str) -> None:
        if not self.project_exists(project_id):
            raise ProjectNotFoundError("Project was not found")

    def _execute(self, statement: str, parameters: tuple[object, ...]) -> None:
        connection = self._connect()
        try:
            connection.execute(statement, parameters)
            connection.commit()
        finally:
            if connection is not self._memory_connection:
                connection.close()

    def _fetchone(self, statement: str, parameters: tuple[object, ...]) -> sqlite3.Row | None:
        connection = self._connect()
        try:
            return connection.execute(statement, parameters).fetchone()
        finally:
            if connection is not self._memory_connection:
                connection.close()

    def _fetchall(self, statement: str, parameters: tuple[object, ...] = ()) -> list[sqlite3.Row]:
        connection = self._connect()
        try:
            return connection.execute(statement, parameters).fetchall()
        finally:
            if connection is not self._memory_connection:
                connection.close()


def _now() -> str:
    return datetime.now(UTC).isoformat()
