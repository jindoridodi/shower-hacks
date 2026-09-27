from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from apps.api.main import create_app
from tests.helpers import create_project


def make_client() -> TestClient:
    database_dir = TemporaryDirectory()
    database_path = Path(database_dir.name) / "test.db"
    client = TestClient(create_app(database_path))
    client.database_dir = database_dir
    return client


def approval_payload(project_id: str) -> dict[str, object]:
    return {
        "projectId": project_id,
        "username": "demo-user",
        "candidate": {
            "url": "https://example.com/demo-user?utm_source=fixture",
            "platform": "example",
            "candidateUsername": "demo-user",
            "confidence": "high",
            "matchReason": "Two providers found the exact public username.",
        },
        "providerEvidence": ["sherlock", "maigret", "sherlock"],
    }


def test_approval_creates_a_canonical_source_with_provenance():
    client = make_client()
    project = create_project(client)

    response = client.post("/api/approvals", json=approval_payload(project["id"]))

    assert response.status_code == 201
    body = response.json()
    assert body["projectId"] == project["id"]
    assert body["canonicalUrl"] == "https://example.com/demo-user"
    assert body["status"] == "pending"
    assert body["username"] == "demo-user"
    assert body["providerEvidence"] == ["sherlock", "maigret"]

    sources = client.get("/sources", params={"project_id": project["id"]})
    assert sources.status_code == 200
    assert [source["id"] for source in sources.json()] == [body["sourceId"]]
    assert sources.json()[0]["approval_status"] == "approved"
    assert sources.json()[0]["is_allowlisted"] is True

    crawls = client.get("/crawls", params={"source_id": body["sourceId"]})
    assert crawls.status_code == 200
    assert crawls.json() == []


def test_approval_requires_matching_candidate_username():
    client = make_client()
    project = create_project(client)
    payload = approval_payload(project["id"])
    payload["candidate"]["candidateUsername"] = "other-user"

    response = client.post("/api/approvals", json=payload)

    assert response.status_code == 422


def test_approval_rejects_a_duplicate_canonical_source():
    client = make_client()
    project = create_project(client)
    payload = approval_payload(project["id"])

    assert client.post("/api/approvals", json=payload).status_code == 201
    duplicate = client.post("/api/approvals", json=payload)

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "duplicate_canonical_url"


def test_approved_sources_are_listed_from_the_canonical_project():
    client = make_client()
    project = create_project(client)
    approved = client.post("/api/approvals", json=approval_payload(project["id"])).json()

    response = client.get("/api/approvals", params={"projectId": project["id"]})

    assert response.status_code == 200
    assert response.json() == [approved]
