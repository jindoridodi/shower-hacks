import json
import unittest
from pathlib import Path

from sqlalchemy import func, select

from apps.api.models import Report
from apps.api.services.communication_draft_generator import (
    CommunicationDraftError,
    generate_communication_draft,
)
from tests.helpers import create_project


ROOT = Path(__file__).resolve().parents[1]


class FakeDraftModel:
    def __init__(self, response: dict) -> None:
        self.response = response

    def generate(self, prompt: str) -> str:
        return json.dumps(self.response)


class CommunicationDraftGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        with (ROOT / "data/fixtures/evidence-excerpts.json").open() as evidence_file:
            self.evidence = json.load(evidence_file)

    def test_returns_a_validated_fixture_draft(self) -> None:
        draft = generate_communication_draft(
            recipient="Alex",
            evidence_excerpts=self.evidence,
            use_fixtures=True,
        )

        self.assertEqual(draft["recipient"], "Alex")
        self.assertEqual(draft["label"], "AI-generated draft — review before use")
        self.assertIs(draft["reviewRequired"], True)

    def test_returns_an_empty_review_only_draft_for_empty_evidence(self) -> None:
        draft = generate_communication_draft(
            recipient="Alex",
            evidence_excerpts=[],
            use_fixtures=True,
        )

        self.assertEqual(draft["body"], "")
        self.assertEqual(draft["sourceIds"], [])
        self.assertIs(draft["reviewRequired"], True)

    def test_rejects_unknown_source_ids(self) -> None:
        model = FakeDraftModel(
            {
                "label": "AI-generated draft — review before use",
                "recipient": "Alex",
                "subject": "Hello",
                "body": "This draft has an invalid source.",
                "sourceIds": ["src_missing"],
                "reviewRequired": True,
            }
        )

        with self.assertRaisesRegex(CommunicationDraftError, "unavailable sourceIds"):
            generate_communication_draft(recipient="Alex", evidence_excerpts=self.evidence, model=model)

    def test_rejects_a_missing_label_or_review_requirement(self) -> None:
        model = FakeDraftModel(
            {
                "label": "Draft",
                "recipient": "Alex",
                "subject": "Hello",
                "body": "This draft has a supported source.",
                "sourceIds": ["src_portfolio"],
                "reviewRequired": False,
            }
        )

        with self.assertRaisesRegex(CommunicationDraftError, "AI-generated label"):
            generate_communication_draft(recipient="Alex", evidence_excerpts=self.evidence, model=model)

    def test_rejects_a_false_review_requirement(self) -> None:
        model = FakeDraftModel(
            {
                "label": "AI-generated draft — review before use",
                "recipient": "Alex",
                "subject": "Hello",
                "body": "This draft has a supported source.",
                "sourceIds": ["src_portfolio"],
                "reviewRequired": False,
            }
        )

        with self.assertRaisesRegex(CommunicationDraftError, "require human review"):
            generate_communication_draft(recipient="Alex", evidence_excerpts=self.evidence, model=model)


def test_draft_endpoint_returns_json_without_writing_a_report(client, session, monkeypatch):
    class ExplodingModel:
        def __init__(self, settings):
            raise AssertionError(settings)

    monkeypatch.setattr("apps.api.routes.generation.OpenAICompatibleTextModel", ExplodingModel)
    project = create_project(client)
    evidence = json.loads((ROOT / "data/fixtures/evidence-excerpts.json").read_text(encoding="utf-8"))
    response = client.post(
        f"/api/projects/{project['id']}/drafts",
        json={"recipient": "Alex", "evidenceExcerpts": evidence, "useFixtures": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "AI-generated draft — review before use"
    assert body["reviewRequired"] is True
    assert body["recipient"] == "Alex"
    assert session.scalar(select(func.count()).select_from(Report)) == 0


if __name__ == "__main__":
    unittest.main()
