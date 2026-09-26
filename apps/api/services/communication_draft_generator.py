from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from apps.api.services.text_model import TextModel


class CommunicationDraftError(ValueError):
    pass


_ROOT = Path(__file__).resolve().parents[3]
_PROMPT_PATH = _ROOT / "packages/prompts/communication_draft.txt"
_DRAFT_FIXTURE_PATH = _ROOT / "data/fixtures/communication-draft.json"
_LABEL = "AI-generated draft — review before use"


def generate_communication_draft(
    *,
    recipient: str,
    evidence_excerpts: Sequence[Mapping[str, Any]],
    model: TextModel | None = None,
    use_fixtures: bool = False,
) -> dict[str, Any]:
    safe_evidence = [excerpt for excerpt in evidence_excerpts if excerpt.get("sensitivityStatus") == "safe"]

    if not safe_evidence:
        return {
            "label": _LABEL,
            "recipient": recipient,
            "subject": "",
            "body": "",
            "sourceIds": [],
            "reviewRequired": True,
        }

    if use_fixtures:
        draft = _load_fixture_draft(recipient)
    else:
        if model is None:
            raise CommunicationDraftError("A draft model is required when fixture mode is disabled.")
        draft = _parse_draft(model.generate(_render_prompt(recipient, safe_evidence)))

    _validate_draft(draft, recipient, safe_evidence)
    return draft


def _load_fixture_draft(recipient: str) -> dict[str, Any]:
    with _DRAFT_FIXTURE_PATH.open() as fixture_file:
        draft = json.load(fixture_file)
    draft["recipient"] = recipient
    return draft


def _render_prompt(recipient: str, evidence_excerpts: Sequence[Mapping[str, Any]]) -> str:
    return (
        _PROMPT_PATH.read_text()
        .replace("{{recipient}}", recipient)
        .replace("{{evidence_excerpts}}", json.dumps(evidence_excerpts, ensure_ascii=False))
    )


def _parse_draft(response: str) -> dict[str, Any]:
    try:
        draft = json.loads(response)
    except json.JSONDecodeError as error:
        raise CommunicationDraftError("The draft model returned invalid JSON.") from error

    if not isinstance(draft, dict):
        raise CommunicationDraftError("The draft model must return a JSON object.")

    return draft


def _validate_draft(
    draft: Mapping[str, Any], recipient: str, evidence_excerpts: Sequence[Mapping[str, Any]]
) -> None:
    required_fields = ("label", "recipient", "subject", "body", "sourceIds", "reviewRequired")
    missing_fields = [field for field in required_fields if field not in draft]
    if missing_fields:
        raise CommunicationDraftError(f"The draft is missing required fields: {', '.join(missing_fields)}.")

    if draft["label"] != _LABEL:
        raise CommunicationDraftError("The draft must use the required AI-generated label.")

    if draft["recipient"] != recipient:
        raise CommunicationDraftError("The draft did not preserve its requested recipient.")

    if not isinstance(draft["subject"], str) or not isinstance(draft["body"], str):
        raise CommunicationDraftError("The draft subject and body must be strings.")

    if draft["reviewRequired"] is not True:
        raise CommunicationDraftError("The draft must require human review.")

    source_ids = draft["sourceIds"]
    if not isinstance(source_ids, list) or not all(isinstance(source_id, str) for source_id in source_ids):
        raise CommunicationDraftError("The draft sourceIds must be a list of strings.")

    if len(source_ids) != len(set(source_ids)):
        raise CommunicationDraftError("The draft contains duplicate sourceIds.")

    evidence_source_ids = {
        excerpt["sourceId"]
        for excerpt in evidence_excerpts
        if isinstance(excerpt.get("sourceId"), str)
    }
    unknown_source_ids = set(source_ids) - evidence_source_ids
    if unknown_source_ids:
        raise CommunicationDraftError(
            f"The draft references unavailable sourceIds: {', '.join(sorted(unknown_source_ids))}."
        )

    if draft["body"].strip() and not source_ids:
        raise CommunicationDraftError("A non-empty draft body must include sourceIds.")

    if not draft["body"].strip() and source_ids:
        raise CommunicationDraftError("An empty draft body must not include sourceIds.")
