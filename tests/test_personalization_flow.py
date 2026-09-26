import json
import unittest
from pathlib import Path

from apps.api.services.communication_draft_generator import generate_communication_draft
from apps.api.services.report_generator import generate_report
from apps.api.services.timeline_extractor import extract_timeline_items


ROOT = Path(__file__).resolve().parents[1]


class PersonalizationFlowTests(unittest.TestCase):
    def test_fixture_flow_returns_only_source_linked_outputs(self) -> None:
        with (ROOT / "data/fixtures/evidence-excerpts.json").open() as evidence_file:
            evidence = json.load(evidence_file)

        report = generate_report(
            report_id="report_flow_001",
            generated_at="2026-09-26T20:00:00Z",
            mode="factual_profile",
            evidence_excerpts=evidence,
            use_fixtures=True,
        )
        timeline = extract_timeline_items(evidence)
        draft = generate_communication_draft(
            recipient="Project collaborator",
            evidence_excerpts=evidence,
            use_fixtures=True,
        )

        evidence_source_ids = {excerpt["sourceId"] for excerpt in evidence}
        for claim in report["claims"]:
            self.assertTrue(claim["sourceIds"])
            self.assertTrue(set(claim["sourceIds"]).issubset(evidence_source_ids))

        self.assertTrue(timeline)
        self.assertTrue(all(item["sourceId"] in evidence_source_ids for item in timeline))
        self.assertEqual(draft["label"], "AI-generated draft — review before use")
        self.assertIs(draft["reviewRequired"], True)
        self.assertTrue(set(draft["sourceIds"]).issubset(evidence_source_ids))


if __name__ == "__main__":
    unittest.main()
