from apps.api.services.evidence import list_safe_excerpts
from tests.helpers import create_project, create_source


def _create_document(client, source_id, text, status, chunk_text):
    response = client.post(
        "/documents",
        json={
            "source_id": source_id,
            "title": "Public source",
            "cleaned_text": text,
            "sensitivity_status": status,
            "chunks": [{"chunk_index": 0, "text": chunk_text}],
        },
    )
    assert response.status_code == 201, response.text


def test_safe_evidence_is_project_scoped_and_excludes_non_clear_documents(client, session):
    project = create_project(client)
    other_project = create_project(client, name="Other")
    clear_source = create_source(client, project["id"], "https://example.com/clear")
    redacted_source = create_source(client, project["id"], "https://example.com/redacted")
    other_source = create_source(client, other_project["id"], "https://example.com/other")

    _create_document(client, clear_source["id"], "Clear public text", "clear", "Clear public text")
    _create_document(client, redacted_source["id"], "Filtered text", "redacted", "Filtered text")
    _create_document(client, other_source["id"], "Other text", "clear", "Other text")

    excerpts = list_safe_excerpts(session, project["id"])

    assert [excerpt.sourceId for excerpt in excerpts] == [clear_source["id"]]
    assert excerpts[0].sourceUrl == "https://example.com/clear"
    assert excerpts[0].sensitivityStatus == "safe"


def test_safe_evidence_rejects_unknown_project_and_invalid_limit(client, session):
    project = create_project(client)

    from apps.api.errors import APIError

    try:
        list_safe_excerpts(session, "missing-project")
    except APIError as error:
        assert error.status_code == 404
    else:
        raise AssertionError("Expected a missing project error")

    try:
        list_safe_excerpts(session, project["id"], limit=0)
    except APIError as error:
        assert error.code == "invalid_evidence_limit"
    else:
        raise AssertionError("Expected an evidence limit error")
