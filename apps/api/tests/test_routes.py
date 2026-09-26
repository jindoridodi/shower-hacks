from fastapi.testclient import TestClient

from apps.api.main import create_app
from apps.api.services.discovery.providers.explicit_url import ExplicitUrlProvider
from apps.api.services.discovery.providers.fixture import FixtureProvider
from apps.api.services.discovery.service import DiscoveryService
from apps.api.services.sources.repository import SQLiteSourceRepository


def make_client() -> TestClient:
    source_repository = SQLiteSourceRepository(":memory:")
    service = DiscoveryService(
        {
            "sherlock": FixtureProvider("sherlock"),
            "maigret": FixtureProvider("maigret"),
            "whatsmyname": FixtureProvider("whatsmyname"),
            "explicit_url": ExplicitUrlProvider(),
        },
        use_fixtures=True,
        source_repository=source_repository,
    )
    return TestClient(create_app(service, source_repository))


def test_health() -> None:
    response = make_client().get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_osint_test_ui_is_served_from_root() -> None:
    response = make_client().get("/")
    assert response.status_code == 200
    assert "Borrowed" in response.text
    assert "/api/discovery" in response.text


def test_discovery_fixture_response_uses_camel_case_contract() -> None:
    response = make_client().post("/api/discovery", json={"query": "demo-user"})
    assert response.status_code == 200
    body = response.json()
    assert body["providersUsed"] == ["sherlock", "maigret", "whatsmyname"]
    assert body["candidates"][0]["candidateUsername"] == "demo-user"
    assert "matchReason" in body["candidates"][0]


def test_discovery_rejects_invalid_inputs() -> None:
    client = make_client()
    for payload in (
        {"query": "bad user", "queryType": "username"},
        {"query": "ftp://example.com", "queryType": "url"},
        {"query": "ftp://example.com"},
        {"query": "https://127.0.0.1", "queryType": "url"},
        {"query": "demo-user", "queryType": "username", "providers": ["sherlock"]},
        {"query": "demo-user", "queryType": "username", "limit": 101},
    ):
        assert client.post("/api/discovery", json=payload).status_code == 422


def test_discovery_automatically_detects_public_urls() -> None:
    response = make_client().post("/api/discovery", json={"query": "https://Example.com/profile/"})
    assert response.status_code == 200
    assert response.json()["providersUsed"] == ["explicit_url"]
    assert response.json()["candidates"][0]["url"] == "https://example.com/profile"


def test_manual_public_source_is_project_scoped_and_merges_into_discovery() -> None:
    client = make_client()
    first_project = client.post("/api/projects", json={"name": "First"}).json()["projectId"]
    second_project = client.post("/api/projects", json={"name": "Second"}).json()["projectId"]

    saved = client.post(
        f"/api/projects/{first_project}/sources",
        json={"username": "Demo-User", "url": "https://Example.com/profile/?utm_source=test#bio"},
    )
    assert saved.status_code == 201
    assert saved.json()["url"] == "https://example.com/profile"
    assert saved.json()["username"] == "demo-user"

    response = client.post(
        "/api/discovery",
        json={"query": "demo-user", "queryType": "username", "projectId": first_project},
    )
    assert response.status_code == 200
    body = response.json()
    candidate = next(item for item in body["candidates"] if item["url"] == "https://example.com/profile")
    assert candidate["confidence"] == "high"
    assert body["providerEvidence"][candidate["url"]] == ["user_supplied"]
    assert len(body["savedSources"]) == 1

    other = client.post(
        "/api/discovery",
        json={"query": "demo-user", "queryType": "username", "projectId": second_project},
    )
    assert other.status_code == 200
    assert other.json()["savedSources"] == []


def test_manual_source_validation_duplicate_listing_and_deletion() -> None:
    client = make_client()
    project_id = client.post("/api/projects", json={"name": "Demo"}).json()["projectId"]
    for url in ("ftp://example.com", "https://user:pass@example.com", "https://localhost", "https://127.0.0.1"):
        assert client.post(f"/api/projects/{project_id}/sources", json={"username": "demo-user", "url": url}).status_code == 422

    created = client.post(
        f"/api/projects/{project_id}/sources",
        json={"username": "demo-user", "url": "https://example.com"},
    )
    assert created.status_code == 201
    assert client.post(
        f"/api/projects/{project_id}/sources",
        json={"username": "demo-user", "url": "https://example.com/"},
    ).status_code == 409
    listed = client.get(f"/api/projects/{project_id}/sources", params={"username": "demo-user"})
    assert len(listed.json()["sources"]) == 1
    assert client.delete(f"/api/projects/{project_id}/sources/{created.json()['sourceId']}").status_code == 204
    assert client.get(f"/api/projects/{project_id}/sources", params={"username": "demo-user"}).json()["sources"] == []


def test_unknown_project_is_not_accepted_for_sources_or_discovery() -> None:
    client = make_client()
    assert client.post(
        "/api/projects/missing/sources", json={"username": "demo-user", "url": "https://example.com"}
    ).status_code == 404
    assert client.post(
        "/api/discovery", json={"query": "demo-user", "queryType": "username", "projectId": "missing"}
    ).status_code == 404
