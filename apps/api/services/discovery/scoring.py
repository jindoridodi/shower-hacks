"""Candidate aggregation, confidence selection, and deterministic ordering."""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.api.services.discovery.models import CandidateSource, ProviderRecord
from apps.api.services.discovery.normalize import canonical_key, normalize_url, platform_for_url

CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class _Aggregate:
    records: list[ProviderRecord] = field(default_factory=list)


def _confidence(records: list[ProviderRecord]) -> str:
    if any(record.direct_input for record in records):
        return "high"
    exact_providers = {record.provider for record in records if record.exact_username_match}
    if len(exact_providers) >= 2:
        return "high"
    if exact_providers:
        return "medium"
    return "low"


def _reason(records: list[ProviderRecord]) -> str:
    user_supplied = next((record for record in records if record.provider == "user_supplied"), None)
    if user_supplied is not None:
        return user_supplied.match_reason
    if any(record.direct_input for record in records):
        return "Explicit public URL supplied by the user."
    exact_providers = sorted({record.provider for record in records if record.exact_username_match})
    if len(exact_providers) >= 2:
        return f"Exact username match reported by independent providers: {', '.join(exact_providers)}."
    if exact_providers:
        return next(record.match_reason for record in records if record.exact_username_match)
    return records[0].match_reason


def candidates_from_records(records: list[ProviderRecord], limit: int) -> list[CandidateSource]:
    """Normalize and merge tool records into the endpoint contract."""

    aggregates: dict[str, _Aggregate] = {}
    for record in records:
        try:
            key = canonical_key(record.url)
        except ValueError:
            continue
        aggregates.setdefault(key, _Aggregate()).records.append(record)

    candidates: list[CandidateSource] = []
    for key, aggregate in aggregates.items():
        first = aggregate.records[0]
        candidates.append(
            CandidateSource(
                url=normalize_url(first.url),
                platform=platform_for_url(first.url, first.platform),
                candidate_username=first.candidate_username,
                confidence=_confidence(aggregate.records),
                match_reason=_reason(aggregate.records),
            )
        )
    return sorted(
        candidates,
        key=lambda item: (CONFIDENCE_ORDER[item.confidence], item.platform, item.url),
    )[:limit]


def provider_evidence_from_records(records: list[ProviderRecord], candidates: list[CandidateSource]) -> dict[str, list[str]]:
    """Return stable provider provenance for the candidates included in a response."""

    evidence: dict[str, set[str]] = {}
    for record in records:
        try:
            canonical_url = normalize_url(record.url)
        except ValueError:
            continue
        evidence.setdefault(canonical_url, set()).add(record.provider)
    return {candidate.url: sorted(evidence.get(candidate.url, set())) for candidate in candidates}
