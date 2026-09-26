import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def app(database_path):
    application = create_app(database_path)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session(app):
    db = app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def isolated_raw_document_storage(tmp_path, monkeypatch):
    monkeypatch.setattr("apps.api.services.crawls.repo_root", lambda: tmp_path)
