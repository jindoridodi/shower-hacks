import sqlite3

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from apps.api.config import repo_root
from apps.api.db import apply_migrations
from apps.api.main import create_app

REQUIRED_TABLES = {
    "projects",
    "sources",
    "crawl_jobs",
    "documents",
    "document_chunks",
    "document_chunks_fts",
    "reports",
    "report_claims",
    "claim_sources",
    "schema_migrations",
}


def test_schema_snapshot_matches_migrations():
    root = repo_root()
    schema = (root / "db" / "schema.sql").read_text(encoding="utf-8")
    migrations = sorted((root / "db" / "migrations").glob("*.sql"))
    combined = "".join(path.read_text(encoding="utf-8") for path in migrations)
    assert schema == combined


def test_migrations_are_repeatable_and_create_tables(tmp_path):
    database_path = tmp_path / "app.db"
    first = apply_migrations(database_path)
    second = apply_migrations(database_path)
    assert first == ["001_initial", "002_raw_document_contract", "002_uniqueness"]
    assert second == []

    connection = sqlite3.connect(database_path)
    try:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
        versions = [
            row[0]
            for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")
        ]
        indexes = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        }
    finally:
        connection.close()
    assert REQUIRED_TABLES <= names
    assert versions == ["001_initial", "002_raw_document_contract", "002_uniqueness"]
    assert "uq_report_claims_report_position" in indexes
    assert "uq_crawl_jobs_one_active" in indexes


def test_create_app_can_open_the_same_database_twice(tmp_path):
    database_path = tmp_path / "app.db"
    first = create_app(database_path)
    second = create_app(database_path)
    try:
        with first.state.engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert connection.execute(text("SELECT 1")).scalar() == 1
    finally:
        first.state.engine.dispose()
        second.state.engine.dispose()


def test_health_and_openapi(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json()["paths"]
    assert "/sources" in paths
    assert "/sources/{source_id}/queue" in paths
    assert "/crawls" in paths
    assert "/crawls/{crawl_id}" in paths
    assert "/documents" in paths
    assert "/search/chunks" in paths


def test_validation_error_shape(client):
    response = client.post("/projects", json={"name": "   "})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "validation_error"
    assert detail["message"] == "Request validation failed"


def test_foreign_keys_reject_orphan_rows(app):
    connection = app.state.engine.connect()
    try:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        connection.rollback()
        with pytest.raises(IntegrityError):
            with connection.begin():
                connection.execute(
                    text(
                        """
                        INSERT INTO sources (
                            id, project_id, url, canonical_url, status, created_at, updated_at
                        ) VALUES (
                            'src', 'missing-project', 'https://example.com/', 'https://example.com/',
                            'pending', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'
                        )
                        """
                    )
                )
        with pytest.raises(IntegrityError):
            with connection.begin():
                connection.execute(
                    text(
                        """
                        INSERT INTO claim_sources (
                            id, claim_id, source_id, excerpt, created_at
                        ) VALUES (
                            'link', 'missing-claim', 'missing-source', 'quoted text',
                            '2026-01-01T00:00:00+00:00'
                        )
                        """
                    )
                )
    finally:
        connection.close()
