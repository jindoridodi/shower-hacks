import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from apps.api.models import ReportClaim
from tests.helpers import create_project, create_source


def test_claim_links_store_excerpts_for_multiple_sources(client):
    project = create_project(client)
    report = client.post("/reports", json={"project_id": project["id"], "title": "Factual profile"})
    assert report.status_code == 201
    report_id = report.json()["id"]
    first = create_source(client, project["id"], "https://example.com/bio")
    second = create_source(client, project["id"], "https://example.com/interests")

    created = client.post(
        f"/reports/{report_id}/claims",
        json={
            "claim_text": "The pages describe a public biography and listed interests.",
            "sources": [
                {"source_id": first["id"], "excerpt": "public biography"},
                {"source_id": second["id"], "excerpt": "listed interests"},
            ],
        },
    )
    assert created.status_code == 201
    claim = created.json()
    assert claim["claim_text"].startswith("The pages describe")
    assert claim["position"] == 0
    excerpts = {item["source_id"]: item["excerpt"] for item in claim["sources"]}
    assert excerpts == {
        first["id"]: "public biography",
        second["id"]: "listed interests",
    }

    extra = client.post(
        f"/report-claims/{claim['id']}/sources",
        json={"source_id": first["id"], "excerpt": "a later paragraph"},
    )
    assert extra.status_code == 201
    later = {item["excerpt"] for item in extra.json()["sources"] if item["source_id"] == first["id"]}
    assert later == {"public biography", "a later paragraph"}

    duplicate = client.post(
        f"/report-claims/{claim['id']}/sources",
        json={"source_id": first["id"], "excerpt": "public biography"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "duplicate_claim_source"

    second_claim = client.post(
        f"/reports/{report_id}/claims",
        json={"claim_text": "The corpus does not establish a private address."},
    )
    assert second_claim.status_code == 201
    assert second_claim.json()["position"] == 1
    assert second_claim.json()["sources"] == []

    fetched = client.get(f"/reports/{report_id}")
    assert fetched.status_code == 200
    assert [item["position"] for item in fetched.json()["claims"]] == [0, 1]


def test_claim_link_requires_a_source_from_the_same_project(client, session):
    project = create_project(client)
    other = create_project(client, name="Other")
    report = client.post("/reports", json={"project_id": project["id"], "title": "Profile"}).json()
    outsider = create_source(client, other["id"], "https://example.org/profile")

    missing = client.post(
        f"/reports/{report['id']}/claims",
        json={
            "claim_text": "A claim without a real source.",
            "sources": [{"source_id": "missing-source", "excerpt": "quoted words"}],
        },
    )
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "source_not_found"
    assert session.scalar(select(func.count()).select_from(ReportClaim)) == 0

    mismatch = client.post(
        f"/reports/{report['id']}/claims",
        json={
            "claim_text": "A claim citing another project.",
            "sources": [{"source_id": outsider["id"], "excerpt": "profile text"}],
        },
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "source_project_mismatch"
    assert session.scalar(select(func.count()).select_from(ReportClaim)) == 0

    blank = client.post(
        f"/reports/{report['id']}/claims",
        json={"claim_text": "   ", "sources": []},
    )
    assert blank.status_code == 422
    assert blank.json()["detail"]["code"] == "validation_error"


def test_database_refuses_to_delete_a_cited_source(client, app):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/cited")
    report = client.post("/reports", json={"project_id": project["id"], "title": "Profile"}).json()
    linked = client.post(
        f"/reports/{report['id']}/claims",
        json={
            "claim_text": "The page contains a public biography.",
            "sources": [{"source_id": source["id"], "excerpt": "public biography"}],
        },
    )
    assert linked.status_code == 201

    connection = app.state.engine.connect()
    try:
        with pytest.raises(IntegrityError):
            with connection.begin():
                connection.execute(
                    text("DELETE FROM sources WHERE id = :source_id"),
                    {"source_id": source["id"]},
                )
    finally:
        connection.close()

    assert client.get(f"/sources/{source['id']}").status_code == 200
