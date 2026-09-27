import pytest
from sqlalchemy import text

from tests.helpers import create_project, create_source

_EXCERPT = "The public page names a community archive."


def test_unknown_output_stores_no_fabricated_citation(client):
    project = create_project(client)
    response = client.post(
        f"/api/projects/{project['id']}/reports/persisted",
        json={
            "report": {
                "id": "report_empty",
                "title": "No evidence available",
                "claims": [],
                "unknowns": ["The corpus does not contain safe evidence for this report."],
            },
            "evidence": [],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["claims"][0]["sources"] == []
    assert body["claims"][0]["claim_text"] == "The corpus does not contain safe evidence for this report."


def test_missing_excerpt_does_not_persist_a_report(client):
    project = create_project(client)
    source = create_source(client, project["id"])
    response = client.post(
        f"/api/projects/{project['id']}/reports/persisted",
        json={
            "report": {
                "id": "report_missing_excerpt",
                "title": "Missing excerpt",
                "claims": [
                    {
                        "id": "claim_missing",
                        "text": "The page says something.",
                        "claimType": "observed",
                        "sourceIds": [source["id"]],
                    }
                ],
            },
            "evidence": [],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "unavailable_evidence"
    assert client.get("/reports/report_missing_excerpt").status_code == 404


def test_sensitive_document_blocks_the_citation(client):
    project = create_project(client)
    source = create_source(client, project["id"])
    stored = client.post(
        "/documents",
        json={
            "source_id": source["id"],
            "cleaned_text": _EXCERPT,
            "sensitivity_status": "sensitive",
        },
    )
    assert stored.status_code == 201
    response = client.post(
        f"/api/projects/{project['id']}/reports/persisted",
        json={
            "report": {
                "id": "report_sensitive_document",
                "title": "Blocked",
                "claims": [
                    {
                        "id": "claim_sensitive_document",
                        "text": "The page names an archive.",
                        "claimType": "observed",
                        "sourceIds": [source["id"]],
                    }
                ],
            },
            "evidence": [
                {
                    "sourceId": source["id"],
                    "text": _EXCERPT,
                    "sensitivityStatus": "safe",
                }
            ],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "sensitive_evidence"
    assert client.get("/reports/report_sensitive_document").status_code == 404


@pytest.mark.parametrize("claim_type", ["observed", "inferred", "uncertain"])
def test_cited_claim_without_sources_does_not_persist(client, claim_type):
    project = create_project(client)
    response = client.post(
        f"/api/projects/{project['id']}/reports/persisted",
        json={
            "report": {
                "id": "report_uncited",
                "title": "Missing sources",
                "claims": [
                    {
                        "id": "claim_uncited",
                        "text": "The page names an archive.",
                        "claimType": claim_type,
                        "sourceIds": [],
                    }
                ],
            },
            "evidence": [],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "claim_requires_evidence"
    assert client.get("/reports/report_uncited").status_code == 404


def test_persisted_report_drops_contradictions_and_generated_at(client, session):
    project = create_project(client)
    source = create_source(client, project["id"])
    response = client.post(
        f"/api/projects/{project['id']}/reports/persisted",
        json={
            "report": {
                "id": "report_ignored_fields",
                "title": "Stored claim",
                "claims": [
                    {
                        "id": "claim_ignored_fields",
                        "text": "The page names an archive.",
                        "claimType": "observed",
                        "sourceIds": [source["id"]],
                    }
                ],
                "contradictions": ["The pages disagree about the year."],
                "generatedAt": "2026-09-26T18:00:00Z",
            },
            "evidence": [
                {
                    "sourceId": source["id"],
                    "text": _EXCERPT,
                    "sensitivityStatus": "safe",
                }
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert "contradictions" not in body
    assert "generatedAt" not in body
    assert body["claims"][0]["claim_text"] == "The page names an archive."
    stored_columns = {
        row[1]
        for table in ("reports", "report_claims", "claim_sources")
        for row in session.execute(text(f"PRAGMA table_info({table})"))
    }
    assert "contradictions" not in stored_columns
    assert "generated_at" not in stored_columns
    assert "generatedAt" not in stored_columns
