from tests.helpers import create_project


def test_generated_routes_ignore_browser_evidence_when_project_has_no_safe_documents(client):
    project = create_project(client)
    browser_supplied_evidence = [
        {
            "sourceId": "browser-source",
            "sourceTitle": "Untrusted browser input",
            "sourceUrl": "https://example.com/untrusted",
            "text": "This must not become report evidence.",
            "sensitivityStatus": "safe",
        }
    ]

    report = client.post(
        f"/api/projects/{project['id']}/reports",
        json={
            "reportId": "report-empty-evidence",
            "useFixtures": True,
            "evidenceExcerpts": browser_supplied_evidence,
        },
    )
    assert report.status_code == 200, report.text
    assert report.json()["claims"] == []
    assert report.json()["unknowns"] == ["The corpus does not contain safe evidence for this report."]

    draft = client.post(
        f"/api/projects/{project['id']}/drafts",
        json={
            "recipient": "Collaborator",
            "useFixtures": True,
            "evidenceExcerpts": browser_supplied_evidence,
        },
    )
    assert draft.status_code == 200, draft.text
    assert draft.json()["body"] == ""
    assert draft.json()["sourceIds"] == []


def test_generated_routes_require_an_existing_project(client):
    report = client.post(
        "/api/projects/missing-project/reports",
        json={"reportId": "report-missing", "useFixtures": True},
    )

    assert report.status_code == 404
    assert report.json()["detail"]["code"] == "project_not_found"
