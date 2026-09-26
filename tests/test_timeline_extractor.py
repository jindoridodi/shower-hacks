import unittest

from apps.api.services.timeline_extractor import extract_timeline_items


class TimelineExtractorTests(unittest.TestCase):
    def test_extracts_and_normalizes_a_written_month_date(self) -> None:
        items = extract_timeline_items(
            [
                {
                    "sourceId": "src_one",
                    "text": "On March 14, 2025, Avery presented a project.",
                    "sensitivityStatus": "safe",
                }
            ]
        )

        self.assertEqual(
            items,
            [
                {
                    "dateText": "March 14, 2025",
                    "normalizedDate": "2025-03-14",
                    "eventText": "On March 14, 2025, Avery presented a project.",
                    "sourceId": "src_one",
                    "confidence": 0.95,
                }
            ],
        )

    def test_keeps_a_year_only_date_unnormalized(self) -> None:
        items = extract_timeline_items(
            [
                {
                    "sourceId": "src_one",
                    "text": "The project was published in 2024.",
                    "sensitivityStatus": "safe",
                }
            ]
        )

        self.assertEqual(items[0]["dateText"], "2024")
        self.assertNotIn("normalizedDate", items[0])
        self.assertEqual(items[0]["confidence"], 0.75)

    def test_keeps_an_ambiguous_numeric_date_unnormalized(self) -> None:
        items = extract_timeline_items(
            [
                {
                    "sourceId": "src_one",
                    "text": "The entry was published on 03/04/2025.",
                    "sensitivityStatus": "safe",
                }
            ]
        )

        self.assertEqual(items[0]["dateText"], "03/04/2025")
        self.assertNotIn("normalizedDate", items[0])
        self.assertEqual(items[0]["confidence"], 0.5)

    def test_ignores_restricted_evidence(self) -> None:
        items = extract_timeline_items(
            [
                {
                    "sourceId": "src_restricted",
                    "text": "On March 14, 2025, this should not be used.",
                    "sensitivityStatus": "restricted",
                }
            ]
        )

        self.assertEqual(items, [])

    def test_returns_no_items_for_empty_evidence(self) -> None:
        self.assertEqual(extract_timeline_items([]), [])


if __name__ == "__main__":
    unittest.main()
