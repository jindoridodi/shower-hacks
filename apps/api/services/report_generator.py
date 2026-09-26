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
        report = _load_fixture_report(report_id, generated_at)
    else:
        if model is None:
            raise ReportGenerationError("A report model is required when fixture mode is disabled.")
        prompt = _render_prompt(mode, report_id, generated_at, safe_evidence)
        report = _parse_report(model.generate(prompt))

    _validate_report(report, report_id, generated_at, safe_evidence)
    return report


def _load_fixture_report(report_id: str, generated_at: str) -> dict[str, Any]:
    with _REPORT_FIXTURE_PATH.open() as fixture_file:
        report = json.load(fixture_file)
    report["id"] = report_id
    report["generatedAt"] = generated_at
    return report


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
