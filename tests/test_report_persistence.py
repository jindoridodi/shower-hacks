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
