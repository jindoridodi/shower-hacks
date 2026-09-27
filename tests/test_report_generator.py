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

    def test_restricted_excerpt_never_reaches_the_model(self) -> None:
        safe = {
            "sourceId": "src_safe",
            "text": "The archive is public.",
            "sensitivityStatus": "safe",
        }
        restricted = {
            "sourceId": "src_restricted",
            "text": "secret-phone-999",
            "sensitivityStatus": "restricted",
        }
        model = FakeReportModel(
            {
                "id": "report_safe_only",
                "title": "Public archive",
                "claims": [
                    {
                        "id": "claim_safe_only",
                        "text": "The archive is public.",
                        "claimType": "observed",
                        "confidence": 0.9,
                        "sourceIds": ["src_safe"],
                    }
                ],
                "contradictions": [],
                "unknowns": [],
                "generatedAt": "2026-09-26T19:00:00Z",
            }
        )

        report = generate_report(
            report_id="report_safe_only",
            generated_at="2026-09-26T19:00:00Z",
            mode="factual_profile",
            evidence_excerpts=[safe, restricted],
            model=model,
        )

        self.assertIn("The archive is public.", model.prompt)
        self.assertNotIn("secret-phone-999", model.prompt)
        self.assertNotIn("src_restricted", model.prompt)
        self.assertNotIn("secret-phone-999", json.dumps(report))

    def test_only_restricted_evidence_skips_the_model(self) -> None:
        class ExplodingModel:
            def generate(self, prompt: str) -> str:
                raise AssertionError(prompt)

        report = generate_report(
            report_id="report_blocked",
            generated_at="2026-09-26T19:00:00Z",
            mode="factual_profile",
            evidence_excerpts=[
                {
                    "sourceId": "src_restricted",
                    "text": "secret-phone-999",
                    "sensitivityStatus": "sensitive",
                }
            ],
            model=ExplodingModel(),
        )

        self.assertEqual(report["claims"], [])
        self.assertEqual(
            report["unknowns"],
            ["The corpus does not contain safe evidence for this report."],
        )

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
