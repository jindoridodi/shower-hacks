import pytest

from apps.api.errors import APIError
from apps.api.services.evidence import list_safe_excerpts
from apps.api.services.reports import get_report, persist_generated_report
from apps.api.models import Report
from tests.helpers import create_project, create_source


def _store_clear_document(client, source_id: str, text: str) -> None:
    response = client.post(
        "/documents",
        json={
            "source_id": source_id,
            "title": "Public profile",
            "cleaned_text": text,
            "sensitivity_status": "clear",
            "chunks": [{"chunk_index": 0, "text": text}],
        },
    )
    assert response.status_code == 201, response.text


def test_safe_project_evidence_persists_claims_and_source_excerpts(client, session):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/profile")
    _store_clear_document(client, source["id"], "A public profile describes archive research.")

    evidence = [excerpt.as_dict() for excerpt in list_safe_excerpts(session, project["id"])]
    persisted = persist_generated_report(
        session,
        project_id=project["id"],
        evidence_excerpts=evidence,
        generated_report={
            "id": "report-evidence-integration",
            "title": "Evidence-backed profile",
            "claims": [
                {
                    "text": "The public profile describes archive research.",
                    "sourceIds": [source["id"]],
                }
            ],
        },
    )

    loaded = get_report(session, persisted.id)
    assert loaded.project_id == project["id"]
    assert loaded.claims[0].claim_text == "The public profile describes archive research."
    assert loaded.claims[0].sources[0].source_id == source["id"]
    assert loaded.claims[0].sources[0].excerpt == "A public profile describes archive research."


def test_generated_report_cannot_persist_a_source_outside_its_project(client, session):
    project = create_project(client)
    other_project = create_project(client, name="Other project")
    source = create_source(client, other_project["id"], "https://example.com/other")
    _store_clear_document(client, source["id"], "Other project evidence.")

    with pytest.raises(APIError, match="unavailable evidence"):
        persist_generated_report(
            session,
            project_id=project["id"],
            evidence_excerpts=[],
            generated_report={
                "id": "report-cross-project",
                "title": "Invalid report",
                "claims": [{"text": "Unsupported", "sourceIds": [source["id"]]}],
            },
        )

    assert session.get(Report, "report-cross-project") is None


def test_empty_safe_evidence_persists_an_unknown_only_report(client, session):
    project = create_project(client)

    persisted = persist_generated_report(
        session,
        project_id=project["id"],
        evidence_excerpts=[],
        generated_report={
            "id": "report-empty-evidence",
            "title": "No evidence available",
            "claims": [],
        },
    )

    assert persisted.claims == []


def test_generated_claim_persists_every_retrieved_chunk_for_a_cited_source(client, session):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/multiple-chunks")
    response = client.post(
        "/documents",
        json={
            "source_id": source["id"],
            "title": "Long public source",
            "cleaned_text": "First excerpt. Second excerpt.",
            "sensitivity_status": "clear",
            "chunks": [
                {"chunk_index": 0, "text": "First excerpt."},
                {"chunk_index": 1, "text": "Second excerpt."},
            ],
        },
    )
    assert response.status_code == 201, response.text

    evidence = [excerpt.as_dict() for excerpt in list_safe_excerpts(session, project["id"])]
    persisted = persist_generated_report(
        session,
        project_id=project["id"],
        evidence_excerpts=evidence,
        generated_report={
            "id": "report-multiple-chunks",
            "title": "Evidence-backed profile",
            "claims": [{"text": "A supported claim.", "sourceIds": [source["id"]]}],
        },
    )

    assert [link.excerpt for link in persisted.claims[0].sources] == [
        "First excerpt.",
        "Second excerpt.",
    ]
