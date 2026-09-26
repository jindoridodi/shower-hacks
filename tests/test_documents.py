import hashlib

from sqlalchemy import func, select

from apps.api.models import Document
from tests.helpers import create_project, create_source


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_document_content_hash_deduplication(client, session):
    project = create_project(client)
    source = create_source(client, project["id"])
    payload = {
        "source_id": source["id"],
        "title": "About",
        "content_type": "text/markdown",
        "cleaned_text": "Public biography",
        "raw_text": "<p>Public biography</p>",
        "sensitivity_status": "clear",
        "chunks": [{"chunk_index": 0, "text": "Public biography"}],
    }
    created = client.post("/documents", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["deduplicated"] is False
    assert body["content_hash"] == _hash("Public biography")
    assert body["sensitivity_status"] == "clear"

    duplicate = client.post(
        "/documents",
        json={
            **payload,
            "raw_text": "<div>Public biography</div>",
            "chunks": [{"chunk_index": 1, "text": "ignored on duplicate"}],
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == body["id"]
    assert duplicate.json()["deduplicated"] is True
    assert duplicate.json()["raw_text"] == "<p>Public biography</p>"

    chunks = client.get(f"/documents/{body['id']}/chunks")
    assert chunks.status_code == 200
    assert len(chunks.json()) == 1

    mismatch = client.post(
        "/documents",
        json={
            "source_id": source["id"],
            "cleaned_text": "A different public page",
            "content_hash": "a" * 64,
        },
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"]["code"] == "content_hash_mismatch"

    changed = client.post(
        "/documents",
        json={"source_id": source["id"], "raw_text": "Only the raw snapshot"},
    )
    assert changed.status_code == 201
    assert changed.json()["content_hash"] == _hash("Only the raw snapshot")
    assert changed.json()["id"] != body["id"]

    stored_source = client.get(f"/sources/{source['id']}").json()
    assert stored_source["content_hash"] == changed.json()["content_hash"]
    assert session.scalar(select(func.count()).select_from(Document).where(Document.source_id == source["id"])) == 2


def test_same_content_on_another_source_is_stored_again(client, session):
    project = create_project(client)
    first = create_source(client, project["id"], "https://example.com/one")
    second = create_source(client, project["id"], "https://example.com/two")
    payload = {"cleaned_text": "Shared public sentence", "sensitivity_status": "unreviewed"}
    left = client.post("/documents", json={**payload, "source_id": first["id"]})
    right = client.post("/documents", json={**payload, "source_id": second["id"]})
    assert left.status_code == 201
    assert right.status_code == 201
    assert left.json()["content_hash"] == right.json()["content_hash"]
    assert left.json()["id"] != right.json()["id"]
    assert session.scalar(select(func.count()).select_from(Document)) == 2


def test_chunk_insertion_order_and_duplicates(client):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/chunks")
    document = client.post(
        "/documents",
        json={"source_id": source["id"], "cleaned_text": "Page used for chunks"},
    )
    assert document.status_code == 201
    document_id = document.json()["id"]

    inserted = client.post(
        f"/documents/{document_id}/chunks",
        json={
            "chunks": [
                {"chunk_index": 1, "text": "second passage"},
                {"chunk_index": 0, "text": "opening passage"},
            ]
        },
    )
    assert inserted.status_code == 201
    listed = client.get(f"/documents/{document_id}/chunks")
    assert [(row["chunk_index"], row["text"]) for row in listed.json()] == [
        (0, "opening passage"),
        (1, "second passage"),
    ]

    duplicate = client.post(
        f"/documents/{document_id}/chunks",
        json={"chunks": [{"chunk_index": 0, "text": "opening passage again"}]},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "duplicate_chunk_index"
    assert len(client.get(f"/documents/{document_id}/chunks").json()) == 2


def test_chunk_full_text_search(client):
    project = create_project(client)
    other = create_project(client, name="Other")
    source = create_source(client, project["id"], "https://example.com/search")
    other_source = create_source(client, other["id"], "https://example.org/search")
    first = client.post(
        "/documents",
        json={
            "source_id": source["id"],
            "cleaned_text": "Alpha document",
            "chunks": [{"chunk_index": 0, "text": "public biography of the subject"}],
        },
    )
    second = client.post(
        "/documents",
        json={
            "source_id": other_source["id"],
            "cleaned_text": "Beta document",
            "chunks": [{"chunk_index": 0, "text": "unrelated gardening notes"}],
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201

    found = client.get("/search/chunks", params={"q": "biography"})
    assert found.status_code == 200
    hits = found.json()
    assert len(hits) == 1
    assert hits[0]["text"] == "public biography of the subject"
    assert hits[0]["source_id"] == source["id"]
    assert hits[0]["document_id"] == first.json()["id"]

    filtered = client.get(
        "/search/chunks",
        params={"q": "biography", "project_id": other["id"]},
    )
    assert filtered.status_code == 200
    assert filtered.json() == []

    empty = client.get("/search/chunks", params={"q": "***"})
    assert empty.status_code == 422
    assert empty.json()["detail"]["code"] == "invalid_search"
