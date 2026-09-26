from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


class ClaimValidationError(ValueError):
    pass


_CLAIM_TYPES = {"observed", "inferred", "uncertain", "unknown"}
_INFERENCE_MARKERS = ("suggests", "likely", "appears", "may ", "might ", "could ", "probably")
_QUOTED_TEXT = re.compile(r'["“]([^"”]+)["”]')


def validate_claims(
    claims: Sequence[Mapping[str, Any]],
    evidence_excerpts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    evidence_by_source_id = {
        excerpt["sourceId"]: excerpt
        for excerpt in evidence_excerpts
        if excerpt.get("sensitivityStatus") == "safe" and isinstance(excerpt.get("sourceId"), str)
    }

    if not evidence_by_source_id and claims:
        raise ClaimValidationError("Claims require at least one safe evidence excerpt.")

    validated_claims = []
    for claim in claims:
        _validate_claim(claim, evidence_by_source_id)
        validated_claims.append(dict(claim))

    return validated_claims


def _validate_claim(claim: Mapping[str, Any], evidence_by_source_id: Mapping[str, Mapping[str, Any]]) -> None:
    claim_id = claim.get("id")
    if not isinstance(claim_id, str) or not claim_id.strip():
        raise ClaimValidationError("Claim id must be a non-empty string.")

    text = claim.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ClaimValidationError(f"Claim {claim_id} must include text.")

    claim_type = claim.get("claimType")
    if claim_type not in _CLAIM_TYPES:
        raise ClaimValidationError(f"Claim {claim_id} has an invalid claimType.")

    confidence = claim.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ClaimValidationError(f"Claim {claim_id} confidence must be between 0 and 1.")

    source_ids = claim.get("sourceIds")
    if not isinstance(source_ids, list) or not source_ids or not all(isinstance(source_id, str) for source_id in source_ids):
        raise ClaimValidationError(f"Claim {claim_id} must include sourceIds.")

    if len(source_ids) != len(set(source_ids)):
        raise ClaimValidationError(f"Claim {claim_id} contains duplicate sourceIds.")

    unknown_source_ids = set(source_ids) - evidence_by_source_id.keys()
    if unknown_source_ids:
        raise ClaimValidationError(f"Claim {claim_id} references unavailable sourceIds: {', '.join(sorted(unknown_source_ids))}.")

    if claim_type == "observed" and any(marker in text.lower() for marker in _INFERENCE_MARKERS):
        raise ClaimValidationError(f"Claim {claim_id} uses inference language but is marked observed.")

    source_text = "\n".join(evidence_by_source_id[source_id].get("text", "") for source_id in source_ids)
    for quote in _QUOTED_TEXT.findall(text):
        if quote not in source_text:
            raise ClaimValidationError(f"Claim {claim_id} contains a quote that is not present in its sources.")
