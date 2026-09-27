"""Evidence-grounded report and draft generation endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.dependencies import get_db
from apps.api.services.communication_draft_generator import (
    CommunicationDraftError,
    generate_communication_draft,
)
from apps.api.services.openai_compatible_text_model import OpenAICompatibleTextModel
from apps.api.services.report_generator import ReportGenerationError, generate_report
from apps.api.services.evidence import list_safe_excerpts
from apps.api.services.reports import persist_generated_report
from apps.api.services.text_model import TextModelError

router = APIRouter(tags=["generation"])


class ReportRequest(BaseModel):
    reportId: str
    generatedAt: str | None = None
    mode: Literal["factual_profile", "uncertainty_report"] = "factual_profile"
    useFixtures: bool = False


class DraftRequest(BaseModel):
    recipient: str
    useFixtures: bool = False


class PingResponse(BaseModel):
    status: Literal["ok"]
    response: str
    model: str


def _model() -> OpenAICompatibleTextModel:
    return OpenAICompatibleTextModel(get_settings())


def _generated_at(value: str | None) -> str:
    return value or datetime.now(timezone.utc).isoformat()


@router.post("/api/llm/ping", response_model=PingResponse)
def llm_ping() -> PingResponse:
    settings = get_settings()
    try:
        model = _model()
        response = model.generate("Reply with exactly: LLM_OK")
    except (TextModelError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        if "model" in locals():
            model.close()

    if response.strip() != "LLM_OK":
        raise HTTPException(status_code=502, detail="LLM responded, but not with the expected ping value.")
    return PingResponse(status="ok", response=response.strip(), model=settings.llm_model)


@router.post("/api/projects/{project_id}/reports")
def create_generated_report(
    project_id: str,
    request: ReportRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    model = None
    try:
        evidence_excerpts = [excerpt.as_dict() for excerpt in list_safe_excerpts(db, project_id)]
        if not request.useFixtures:
            model = _model()
        generated = generate_report(
            report_id=request.reportId,
            generated_at=_generated_at(request.generatedAt),
            mode=request.mode,
            evidence_excerpts=evidence_excerpts,
            model=model,
            use_fixtures=request.useFixtures,
        )
        persist_generated_report(
            db,
            project_id=project_id,
            generated_report=generated,
            evidence_excerpts=evidence_excerpts,
        )
        return generated
    except (ReportGenerationError, TextModelError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        if model is not None:
            model.close()


@router.post("/api/projects/{project_id}/drafts")
def create_draft(
    project_id: str,
    request: DraftRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    model = None
    try:
        evidence_excerpts = [excerpt.as_dict() for excerpt in list_safe_excerpts(db, project_id)]
        if not request.useFixtures:
            model = _model()
        return generate_communication_draft(
            recipient=request.recipient,
            evidence_excerpts=evidence_excerpts,
            model=model,
            use_fixtures=request.useFixtures,
        )
    except (CommunicationDraftError, TextModelError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        if model is not None:
            model.close()
