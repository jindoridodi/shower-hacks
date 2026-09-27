import json
import unittest
from pathlib import Path

from apps.api.services.report_generator import ReportGenerationError, generate_report


ROOT = Path(__file__).resolve().parents[1]


class FakeReportModel:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompt = ""

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return json.dumps(self.response)


class ReportGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        with (ROOT / "data/fixtures/evidence-excerpts.json").open() as evidence_file:
            self.evidence = json.load(evidence_file)

    def test_returns_a_validated_fixture_report(self) -> None:
        report = generate_report(
            report_id="report_test_001",
            generated_at="2026-09-26T19:00:00Z",
            mode="factual_profile",
            evidence_excerpts=self.evidence,
            use_fixtures=True,
        )

        self.assertEqual(report["id"], "report_test_001")
        self.assertEqual(report["generatedAt"], "2026-09-26T19:00:00Z")
        self.assertEqual(len(report["claims"]), 3)

    def test_returns_an_unknown_result_for_empty_evidence(self) -> None:
        report = generate_report(
            report_id="report_test_002",
            generated_at="2026-09-26T19:00:00Z",
            mode="factual_profile",
            evidence_excerpts=[],
            use_fixtures=True,
        )

        self.assertEqual(report["claims"], [])
        self.assertEqual(report["unknowns"], ["The corpus does not contain safe evidence for this report."])

    def test_fixture_mode_uses_runtime_source_ids_for_non_seed_projects(self) -> None:
        evidence = [
            {
                "sourceId": "database-source-id",
                "sourceTitle": "Project source",
                "sourceUrl": "https://example.com/project-source",
                "text": "A public project source describes archive research.",
                "sensitivityStatus": "safe",
            }
        ]

        report = generate_report(
            report_id="report-runtime-fixture",
            generated_at="2026-09-26T20:00:00Z",
            mode="factual_profile",
            evidence_excerpts=evidence,
            use_fixtures=True,
        )

        self.assertEqual(report["claims"][0]["sourceIds"], ["database-source-id"])
        self.assertEqual(report["claims"][0]["text"], evidence[0]["text"])

    def test_renders_the_requested_prompt_and_validates_model_output(self) -> None:
        model = FakeReportModel(
            {
                "id": "report_test_003",
                "title": "Uncertainty report",
                "claims": [
                    {
                        "id": "claim_test_003",
                        "text": "The available source does not establish whether similar presentations are recurring.",
                        "claimType": "uncertain",
                        "confidence": 0.58,
                        "sourceIds": ["src_talk"],
                    }
                ],
                "contradictions": [],
                "unknowns": ["The corpus does not establish a complete presentation history."],
                "generatedAt": "2026-09-26T19:00:00Z",
            }
        )

        report = generate_report(
            report_id="report_test_003",
            generated_at="2026-09-26T19:00:00Z",
            mode="uncertainty_report",
            evidence_excerpts=self.evidence,
            model=model,
        )

        self.assertEqual(report["title"], "Uncertainty report")
        self.assertIn("evidence-backed uncertainty report", model.prompt)

    def test_rejects_invalid_model_claims(self) -> None:
        model = FakeReportModel(
            {
                "id": "report_test_004",
                "title": "Invalid report",
                "claims": [
                    {
                        "id": "claim_test_004",
                        "text": "A claim with an unavailable citation.",
                        "claimType": "observed",
                        "confidence": 0.9,
                        "sourceIds": ["src_missing"],
                    }
                ],
                "contradictions": [],
                "unknowns": [],
                "generatedAt": "2026-09-26T19:00:00Z",
            }
        )

        with self.assertRaisesRegex(ReportGenerationError, "unavailable sourceIds"):
            generate_report(
                report_id="report_test_004",
                generated_at="2026-09-26T19:00:00Z",
                mode="factual_profile",
                evidence_excerpts=self.evidence,
                model=model,
            )


if __name__ == "__main__":
    unittest.main()
