from apps.api.services.discovery.models import ProviderRecord
from apps.api.services.discovery.scoring import candidates_from_records


def test_duplicate_candidates_merge_provider_evidence_and_promote_two_exact_matches() -> None:
    candidates = candidates_from_records(
        [
            ProviderRecord("https://github.com/demo-user?utm_source=x", "github", "demo-user", True, "sherlock", "Sherlock match."),
            ProviderRecord("https://github.com/demo-user", "github", "demo-user", True, "fixture", "Fixture match."),
        ],
        limit=25,
    )
    assert len(candidates) == 1
    assert candidates[0].confidence == "high"
    assert "fixture, sherlock" in candidates[0].match_reason


def test_direct_input_is_high_confidence_and_sorted_first() -> None:
    candidates = candidates_from_records(
        [
            ProviderRecord("https://example.com/weak", None, "demo", False, "sherlock", "Weak match."),
            ProviderRecord("https://example.org", None, None, False, "explicit_url", "Direct.", direct_input=True),
        ],
        limit=25,
    )
    assert [candidate.confidence for candidate in candidates] == ["high", "low"]
