import json
import unittest
from pathlib import Path

from apps.api.services.claim_validation import ClaimValidationError, validate_claims


ROOT = Path(__file__).resolve().parents[1]


class ClaimValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = [
            {
                "sourceId": "src_one",
                "text": "The public page says Avery presented a project on March 14.",
                "sensitivityStatus": "safe",
            }
        ]
        self.claim = {
            "id": "claim_one",
            "text": "Avery presented a project on March 14.",
            "claimType": "observed",
            "confidence": 0.9,
            "sourceIds": ["src_one"],
        }

    def test_accepts_a_valid_claim(self) -> None:
        self.assertEqual(validate_claims([self.claim], self.evidence), [self.claim])

    def test_rejects_missing_source_ids(self) -> None:
        self.claim["sourceIds"] = []
        with self.assertRaisesRegex(ClaimValidationError, "sourceIds"):
            validate_claims([self.claim], self.evidence)

    def test_rejects_unknown_source_ids(self) -> None:
        self.claim["sourceIds"] = ["src_missing"]
        with self.assertRaisesRegex(ClaimValidationError, "unavailable sourceIds"):
            validate_claims([self.claim], self.evidence)

    def test_rejects_observed_inference(self) -> None:
        self.claim["text"] = "The corpus suggests Avery presented a project."
        with self.assertRaisesRegex(ClaimValidationError, "inference language"):
            validate_claims([self.claim], self.evidence)

    def test_rejects_an_unsupported_quote(self) -> None:
        self.claim["text"] = 'Avery said "This quote is not in the source."'
        with self.assertRaisesRegex(ClaimValidationError, "quote"):
            validate_claims([self.claim], self.evidence)

    def test_returns_no_claims_for_empty_evidence(self) -> None:
        self.assertEqual(validate_claims([], []), [])

    def test_validates_the_report_fixture(self) -> None:
        with (ROOT / "data/fixtures/evidence-excerpts.json").open() as evidence_file:
            evidence = json.load(evidence_file)
        with (ROOT / "data/fixtures/report.json").open() as report_file:
            report = json.load(report_file)

        self.assertEqual(validate_claims(report["claims"], evidence), report["claims"])


if __name__ == "__main__":
    unittest.main()
