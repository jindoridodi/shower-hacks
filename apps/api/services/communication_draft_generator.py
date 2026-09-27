from __future__ import annotations

import json
import re
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
_TONE_INSTRUCTIONS = {
    "romantic": "Write warm, sincere, tender, confident romantic prose. Explain why literal details feel special, with occasional playful flirtation. Do not mention social media, profiles, research, data, or AI.",
    "poetic": "Write lyrical, intimate, atmospheric prose with vivid imagery and varied rhythm. Turn literal details into poetic observations without inventing facts or mentioning their source.",
    "chaotic": "Write affectionate, fast-paced, playful prose with dramatic interruptions, harmless hyperbole, and occasional ALL CAPS. Keep every joke tied to literal details and do not mention their source.",
    "unhinged": "Write affectionate, comically overdramatic prose that escalates from ordinary details. No threats, surveillance, possessiveness, sexual harassment, invented facts, or mentions of their source.",
}


def generate_communication_draft(
    *,
    recipient: str,
    tone: str = "romantic",
    plain_text: bool = False,
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
        response = model.generate(_render_prompt(recipient, safe_evidence, tone, plain_text))
        if plain_text:
            draft = _text_draft(recipient, response, safe_evidence, tone)
        else:
            generate_json = getattr(model, "generate_json", model.generate)
            response = generate_json(_render_prompt(recipient, safe_evidence, tone, plain_text))
            try:
                draft = _parse_draft(response)
            except CommunicationDraftError as error:
                if str(error) != "The draft model returned invalid JSON.":
                    raise
                draft = _fallback_draft(recipient, safe_evidence, tone)

    _validate_draft(draft, recipient, safe_evidence)
    return draft


def _load_fixture_draft(recipient: str) -> dict[str, Any]:
    with _DRAFT_FIXTURE_PATH.open() as fixture_file:
        draft = json.load(fixture_file)
    draft["recipient"] = recipient
    return draft


def _render_prompt(recipient: str, evidence_excerpts: Sequence[Mapping[str, Any]], tone: str = "romantic", plain_text: bool = False) -> str:
    return (
        _PROMPT_PATH.read_text()
        .replace("{{recipient}}", recipient)
        .replace("{{tone}}", _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["romantic"]))
        .replace("{{output_format}}", "Return only the letter text, with no JSON or Markdown fence." if plain_text else "Return JSON only, with the shape above.")
        .replace("{{evidence_excerpts}}", json.dumps(evidence_excerpts, ensure_ascii=False))
    )


def _text_draft(recipient: str, body: str, evidence_excerpts: Sequence[Mapping[str, Any]], tone: str) -> dict[str, Any]:
    if not body.strip():
        return _fallback_draft(recipient, evidence_excerpts, tone)
    try:
        return _parse_draft(body)
    except CommunicationDraftError:
        pass
    clean_body = re.sub(r"\s*\(instagram:[^)]+\)", "", body).strip()
    return {"label": _LABEL, "recipient": recipient, "subject": "A note for you", "body": clean_body, "sourceIds": list(dict.fromkeys(excerpt["sourceId"] for excerpt in evidence_excerpts if isinstance(excerpt.get("sourceId"), str))), "reviewRequired": True}


def _parse_draft(response: str) -> dict[str, Any]:
    try:
        draft = json.loads(_json_object(response))
    except json.JSONDecodeError as error:
        raise CommunicationDraftError("The draft model returned invalid JSON.") from error

    if not isinstance(draft, dict):
        raise CommunicationDraftError("The draft model must return a JSON object.")

    return draft


def _json_object(response: str) -> str:
    body = response.strip()
    if body.startswith("```") and body.endswith("```"):
        body = body.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
    start = body.find("{")
    end = body.rfind("}")
    return body[start : end + 1] if start >= 0 and end >= start else body


def _fallback_draft(recipient: str, evidence_excerpts: Sequence[Mapping[str, Any]], tone: str) -> dict[str, Any]:
    excerpts = [excerpt.get("text", "").strip()[:500] for excerpt in evidence_excerpts]
    source_ids = list(dict.fromkeys(excerpt["sourceId"] for excerpt in evidence_excerpts if isinstance(excerpt.get("sourceId"), str)))
    return {
        "label": _LABEL,
        "recipient": recipient,
        "subject": "A note about your public posts",
        "body": f"Dear {recipient},\n\n" + "\n\n".join(f"“{text}”" for text in excerpts if text) + f"\n\n{_fallback_closing(tone)}",
        "sourceIds": source_ids,
        "reviewRequired": True,
    }


def _fallback_closing(tone: str) -> str:
    return {
        "romantic": "There is something quietly lovely in the details you choose to share.\n\nWith admiration,\n[your name]",
        "poetic": "Even small details can leave a little light behind.\n\nThinking of that light,\n[your name]",
        "chaotic": "Honestly, these details have rearranged the furniture in my brain.\n\nFondly and dramatically,\n[your name]",
        "unhinged": "I was prepared to be normal about this. Clearly, that plan has failed.\n\nWith disproportionate admiration,\n[your name]",
    }.get(tone, "With appreciation,\n[your name]")


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
