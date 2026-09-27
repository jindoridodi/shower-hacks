from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from apps.api.services.claim_validation import ClaimValidationError, validate_claims
from apps.api.services.text_model import TextModel


ReportMode = Literal["factual_profile", "uncertainty_report"]


class ReportGenerationError(ValueError):
    pass


_ROOT = Path(__file__).resolve().parents[3]
_PROMPT_PATHS = {
    "factual_profile": _ROOT / "packages/prompts/factual_profile.txt",
    "uncertainty_report": _ROOT / "packages/prompts/uncertainty_report.txt",
}
_REPORT_FIXTURE_PATH = _ROOT / "data/fixtures/report.json"


def generate_report(
    *,
    report_id: str,
    generated_at: str,
    mode: ReportMode,
    evidence_excerpts: Sequence[Mapping[str, Any]],
    model: TextModel | None = None,
    use_fixtures: bool = False,
) -> dict[str, Any]:
    safe_evidence = [excerpt for excerpt in evidence_excerpts if excerpt.get("sensitivityStatus") == "safe"]

    if not safe_evidence:
        return {
            "id": report_id,
            "title": "No evidence available",
            "claims": [],
            "contradictions": [],
            "unknowns": ["The corpus does not contain safe evidence for this report."],
            "generatedAt": generated_at,
        }

    if use_fixtures:
        report = _load_fixture_report(report_id, generated_at, safe_evidence)
    else:
        if model is None:
            raise ReportGenerationError("A report model is required when fixture mode is disabled.")
        prompt = _render_prompt(mode, report_id, generated_at, safe_evidence)
        report = _parse_report(model.generate(prompt))

    _validate_report(report, report_id, generated_at, safe_evidence)
    return report


def _load_fixture_report(
    report_id: str,
    generated_at: str,
    evidence_excerpts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    with _REPORT_FIXTURE_PATH.open() as fixture_file:
        report = json.load(fixture_file)
    report["id"] = report_id
    report["generatedAt"] = generated_at

    fixture_source_urls = _fixture_source_urls()
    runtime_source_ids_by_url = {
        excerpt.get("sourceUrl"): excerpt.get("sourceId")
        for excerpt in evidence_excerpts
        if isinstance(excerpt.get("sourceUrl"), str) and isinstance(excerpt.get("sourceId"), str)
    }
    remapped_claims = []
    for claim in report.get("claims", []):
        source_ids = claim.get("sourceIds")
        if not isinstance(source_ids, list):
            return _direct_fixture_report(report_id, generated_at, evidence_excerpts)
        remapped_ids = [runtime_source_ids_by_url.get(fixture_source_urls.get(source_id)) for source_id in source_ids]
        if any(not isinstance(source_id, str) for source_id in remapped_ids):
            return _direct_fixture_report(report_id, generated_at, evidence_excerpts)
        remapped_claims.append({**claim, "sourceIds": remapped_ids})
    report["claims"] = remapped_claims
    return report


def _fixture_source_urls() -> dict[str, str]:
    fixture_evidence_path = _ROOT / "data/fixtures/evidence-excerpts.json"
    with fixture_evidence_path.open() as fixture_file:
        fixture_evidence = json.load(fixture_file)
    return {
        item["sourceId"]: item["sourceUrl"]
        for item in fixture_evidence
        if isinstance(item, dict)
        and isinstance(item.get("sourceId"), str)
        and isinstance(item.get("sourceUrl"), str)
    }


def _direct_fixture_report(
    report_id: str,
    generated_at: str,
    evidence_excerpts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Fallback fixture output for a project without the seed fixture URLs."""
    claims = []
    for index, excerpt in enumerate(evidence_excerpts, start=1):
        source_id = excerpt.get("sourceId")
        text = excerpt.get("text")
        if not isinstance(source_id, str) or not isinstance(text, str) or not text.strip():
            continue
        claims.append(
            {
                "id": f"fixture-claim-{index}",
                "text": text,
                "claimType": "observed",
                "confidence": 0.9,
                "sourceIds": [source_id],
            }
        )
    return {
        "id": report_id,
        "title": "Fixture evidence report",
        "claims": claims,
        "contradictions": [],
        "unknowns": [],
        "generatedAt": generated_at,
    }


def _render_prompt(
    mode: ReportMode,
    report_id: str,
    generated_at: str,
    evidence_excerpts: Sequence[Mapping[str, Any]],
) -> str:
    try:
        prompt_template = _PROMPT_PATHS[mode].read_text()
    except KeyError as error:
        raise ReportGenerationError(f"Unsupported report mode: {mode}.") from error

    return (
        prompt_template.replace("{{report_id}}", report_id)
        .replace("{{generated_at}}", generated_at)
        .replace("{{evidence_excerpts}}", json.dumps(evidence_excerpts, ensure_ascii=False))
    )


def _parse_report(response: str) -> dict[str, Any]:
    try:
        report = json.loads(response)
    except json.JSONDecodeError as error:
        raise ReportGenerationError("The report model returned invalid JSON.") from error

    if not isinstance(report, dict):
        raise ReportGenerationError("The report model must return a JSON object.")

    return report


def _validate_report(
    report: Mapping[str, Any],
    report_id: str,
    generated_at: str,
    evidence_excerpts: Sequence[Mapping[str, Any]],
) -> None:
    required_fields = ("id", "title", "claims", "contradictions", "unknowns", "generatedAt")
    missing_fields = [field for field in required_fields if field not in report]
    if missing_fields:
        raise ReportGenerationError(f"The report is missing required fields: {', '.join(missing_fields)}.")

    if report["id"] != report_id or report["generatedAt"] != generated_at:
        raise ReportGenerationError("The report did not preserve its requested id and generatedAt values.")

    if not isinstance(report["title"], str):
        raise ReportGenerationError("The report title must be a string.")

    if not isinstance(report["claims"], list):
        raise ReportGenerationError("The report claims must be a list.")

    if not isinstance(report["contradictions"], list) or not all(
        isinstance(item, str) for item in report["contradictions"]
    ):
        raise ReportGenerationError("The report contradictions must be strings.")

    if not isinstance(report["unknowns"], list) or not all(isinstance(item, str) for item in report["unknowns"]):
        raise ReportGenerationError("The report unknowns must be strings.")

    try:
        validate_claims(report["claims"], evidence_excerpts)
    except ClaimValidationError as error:
        raise ReportGenerationError(str(error)) from error
