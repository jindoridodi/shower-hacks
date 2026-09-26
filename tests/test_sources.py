import pytest

from apps.api.services.urls import InvalidURL, canonicalize_url
from tests.helpers import create_project, create_source


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("HTTPS://Example.COM:443/a//b/?z=1&a=2#frag", "https://example.com/a/b?a=2&z=1"),
        ("https://example.com/docs/", "https://example.com/docs"),
        ("https://example.com/%7Euser", "https://example.com/~user"),
        ("http://example.com:80", "http://example.com/"),
        ("https://example.com:8443/x", "https://example.com:8443/x"),
        ("https://example.com/a/./b/../c", "https://example.com/a/c"),
    ],
)
def test_url_canonicalization_rules(raw, canonical):
    assert canonicalize_url(raw) == canonical


@pytest.mark.parametrize(
    "raw",
    [
        "ftp://example.com/file",
        "https://user:secret@example.com/private",
        "https://example.com/a b",
        "not a url",
        "",
    ],
)
def test_url_canonicalization_rejects_unsupported_urls(raw):
    with pytest.raises(InvalidURL):
        canonicalize_url(raw)


def test_project_and_source_creation(client):
    created = create_project(client, name="Ada", description="Public biography pages")
    fetched = client.get(f"/projects/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Ada"
    assert fetched.json()["description"] == "Public biography pages"

    missing = client.get("/projects/missing")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "project_not_found"

    source = create_source(client, created["id"], "HTTPS://Example.COM/docs/#section")
    assert source["url"] == "HTTPS://Example.COM/docs/#section"
    assert source["canonical_url"] == "https://example.com/docs"
    assert source["status"] == "pending"
    assert source["content_hash"] is None
    assert source["scraped_at"] is None

    listed = client.get("/sources", params={"project_id": created["id"]})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [source["id"]]


def test_duplicate_canonical_urls_are_rejected_inside_a_project(client):
    project = create_project(client)
    original = create_source(client, project["id"], "https://example.com/docs/")
    duplicate = client.post(
        "/sources",
        json={"project_id": project["id"], "url": "https://Example.com/docs#notes"},
    )
    assert duplicate.status_code == 409
    body = duplicate.json()["detail"]
    assert body["code"] == "duplicate_canonical_url"
    assert body["existing_id"] == original["id"]

    listed = client.get("/sources", params={"project_id": project["id"]})
    assert len(listed.json()) == 1


def test_same_canonical_url_can_exist_in_another_project(client):
    first = create_project(client, name="One")
    second = create_project(client, name="Two")
    create_source(client, first["id"], "https://example.com/docs")
    other = create_source(client, second["id"], "https://example.com/docs")
    assert other["canonical_url"] == "https://example.com/docs"


def test_http_and_https_are_distinct_sources(client):
    project = create_project(client)
    create_source(client, project["id"], "http://example.com/docs")
    secure = create_source(client, project["id"], "https://example.com/docs")
    assert secure["canonical_url"] == "https://example.com/docs"


def test_invalid_url_and_missing_project_are_clear_errors(client):
    project = create_project(client)
    invalid = client.post(
        "/sources",
        json={"project_id": project["id"], "url": "https://user:secret@example.com/a"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "invalid_url"

    missing = client.post(
        "/sources",
        json={"project_id": "missing-project", "url": "https://example.com/"},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "project_not_found"
