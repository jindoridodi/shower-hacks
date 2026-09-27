import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from apps.api.config import repo_root
from apps.api.services.crawls import ingest_scraped_page
from apps.api.services.firecrawl import ScrapedPage
from apps.api.services.hashing import sha256_text
from tests.helpers import approve_source, create_project, create_source

_FIXTURE = json.loads((repo_root() / "data" / "fixtures" / "report.json").read_text(encoding="utf-8"))
_PAGE = _FIXTURE["claims"][0]["text"]
_UNKNOWN = _FIXTURE["unknowns"][0]


def test_public_page_flow_persists_a_cited_report(client, session):
    project = create_project(client, name="Avery")
    other = create_project(client, name="Other")
    source = create_source(client, project["id"], "HTTPS://Example.COM/archives/")
    assert source["url"] == "HTTPS://Example.COM/archives/"
    assert source["canonical_url"] == "https://example.com/archives"
    assert source["status"] == "pending"
    approve_source(client, source["id"])

    rejected = client.patch("/api/crawls/missing", json={"status": "complete"})
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "validation_error"

    queued = client.post(
        f"/api/projects/{project['id']}/crawls",
        json={"source_id": source["id"]},
    )
    assert queued.status_code == 201
    job = queued.json()
    assert job["status"] == "queued"
    assert job["created_at"]
    assert job["started_at"] is None
    assert job["completed_at"] is None
    assert client.get(f"/api/crawls/{job['id']}").json() == job

    mismatch = client.post(
        f"/api/projects/{other['id']}/crawls",
        json={"source_id": source["id"]},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "source_project_mismatch"

    document = ingest_scraped_page(
        session,
        job["id"],
        ScrapedPage(
            url="https://example.com/archives",
            markdown=_PAGE,
            title="Archives",
            raw_html=f"<p>{_PAGE}</p>",
        ),
    )
    stored = client.get(f"/documents/{document.id}")
    assert stored.status_code == 200
    stored_body = stored.json()
    assert stored_body["content_hash"] == sha256_text(_PAGE)
    assert stored_body["cleaned_text"] == _PAGE

    finished = client.get(f"/api/crawls/{job['id']}").json()
    assert finished["status"] == "succeeded"
    assert finished["started_at"]
    assert finished["completed_at"]
    source_body = client.get(f"/sources/{source['id']}").json()
    assert source_body["status"] == "succeeded"
    assert source_body["content_hash"] == stored_body["content_hash"]
    assert source_body["scraped_at"] == finished["completed_at"]

    duplicate = client.post(
        "/documents",
        json={
            "source_id": source["id"],
            "cleaned_text": _PAGE,
            "sensitivity_status": "unreviewed",
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["deduplicated"] is True
    assert duplicate.json()["id"] == document.id
    assert client.get(f"/sources/{source['id']}").json()["content_hash"] == stored_body["content_hash"]

    chunks = client.get(f"/documents/{document.id}/chunks")
    assert chunks.status_code == 200
    assert len(chunks.json()) == 1
    assert chunks.json()[0]["document_id"] == document.id
    assert chunks.json()[0]["chunk_index"] == 0
    assert chunks.json()[0]["text"] == _PAGE

    duplicate_chunk = client.post(
        f"/documents/{document.id}/chunks",
        json={"chunks": [{"chunk_index": 0, "text": _PAGE}]},
    )
    assert duplicate_chunk.status_code == 409
    assert duplicate_chunk.json()["detail"]["code"] == "duplicate_chunk_index"
    found = client.get("/search/chunks", params={"q": "storytelling", "project_id": project["id"]})
    assert found.status_code == 200
    assert found.json()[0]["text"] == _PAGE
    assert found.json()[0]["source_id"] == source["id"]

    corpus = client.get(f"/api/projects/{project['id']}/corpus")
    assert corpus.status_code == 200
    assert corpus.json()["documents"][0]["chunks"][0]["text"] == _PAGE

    payload = _report_payload(source["id"], report_id=_FIXTURE["id"], claim_id=_FIXTURE["claims"][0]["id"])
    created = client.post(f"/api/projects/{project['id']}/reports/persisted", json=payload)
    assert created.status_code == 201
    cited, unknown = _split_claims(created.json())
    assert cited["sources"][0]["source_id"] == source["id"]
    assert cited["sources"][0]["excerpt"] == _PAGE
    assert unknown["sources"] == []

    retried = client.post(f"/api/projects/{project['id']}/reports/persisted", json=payload)
    assert retried.status_code == 200
    retried_claim, _unknown = _split_claims(retried.json())
    assert len(retried_claim["sources"]) == 1
    assert retried_claim["sources"][0]["excerpt"] == _PAGE

    fetched = client.get(f"/api/reports/{_FIXTURE['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == client.get(f"/reports/{_FIXTURE['id']}").json()
    fetched_claim, _unknown = _split_claims(fetched.json())
    assert fetched_claim["sources"][0]["excerpt"] == _PAGE

    with pytest.raises(IntegrityError):
        session.execute(text("DELETE FROM sources WHERE id = :source_id"), {"source_id": source["id"]})
        session.commit()
    session.rollback()

    other_source = create_source(client, other["id"], "https://example.org/profile")
    isolated = client.post(
        f"/api/projects/{project['id']}/reports/persisted",
        json=_report_payload(other_source["id"], report_id="report_isolated", claim_id="claim_isolated"),
    )
    assert isolated.status_code == 409
    assert isolated.json()["detail"]["code"] == "source_project_mismatch"
    assert client.get("/reports/report_isolated").status_code == 404

    before = client.get(f"/api/reports/{_FIXTURE['id']}").json()
    poisoned = _report_payload(source["id"], report_id=_FIXTURE["id"], claim_id=_FIXTURE["claims"][0]["id"])
    poisoned["evidence"][0]["sensitivityStatus"] = "sensitive"
    poisoned["report"]["title"] = "Should not replace the stored report"
    rejected_evidence = client.post(
        f"/api/projects/{project['id']}/reports/persisted",
        json=poisoned,
    )
    assert rejected_evidence.status_code == 409
    assert rejected_evidence.json()["detail"]["code"] == "sensitive_evidence"
    assert client.get(f"/api/reports/{_FIXTURE['id']}").json() == before


def _report_payload(source_id: str, report_id: str, claim_id: str) -> dict:
    return {
        "report": {
            "id": report_id,
            "title": _FIXTURE["title"],
            "claims": [
                {
                    "id": claim_id,
                    "text": _PAGE,
                    "claimType": "observed",
                    "sourceIds": [source_id],
                }
            ],
            "unknowns": [_UNKNOWN],
            "contradictions": [],
            "generatedAt": "2026-09-26T18:00:00Z",
        },
        "evidence": [
            {
                "sourceId": source_id,
                "text": _PAGE,
                "sensitivityStatus": "safe",
            }
        ],
    }


def _split_claims(body: dict) -> tuple[dict, dict]:
    cited = next(claim for claim in body["claims"] if claim["sources"])
    unknown = next(claim for claim in body["claims"] if claim["claim_text"] == _UNKNOWN)
    return cited, unknown
