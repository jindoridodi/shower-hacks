<<<<<<< HEAD
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.db import apply_migrations, make_engine, make_session_factory
from apps.api.dependencies import get_db
from apps.api.errors import APIError
from apps.api.routes import crawls, documents, projects, reports, sources


def create_app(database_path: Path | None = None) -> FastAPI:
    path = database_path or get_settings().database_path
    apply_migrations(path)
    engine = make_engine(path)
    app = FastAPI(
        title="Borrowed Intimacy API",
        version="0.1.0",
        summary="Source, crawl, document, and evidence API",
    )
    app.state.engine = engine
    app.state.database_path = path
    app.state.session_factory = make_session_factory(engine)
    app.include_router(projects.router)
    app.include_router(sources.router)
    app.include_router(crawls.router)
    app.include_router(documents.router)
    app.include_router(reports.router)
    _register_handlers(app)

    @app.get("/health", tags=["health"])
    def health(db: Session = Depends(get_db)) -> dict[str, str]:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


def _register_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(_request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.payload})

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "errors": jsonable_encoder(exc.errors()),
                }
            },
        )


def __getattr__(name: str) -> FastAPI:
    # Create the dev app on first attribute access so importing create_app
    # from tests does not open data/borrowed_intimacy.db.
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
=======
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from apps.api.config import get_settings
from apps.api.services.communication_draft_generator import (
    CommunicationDraftError,
    generate_communication_draft,
)
from apps.api.services.openai_compatible_text_model import OpenAICompatibleTextModel
from apps.api.services.report_generator import ReportGenerationError, generate_report
from apps.api.services.text_model import TextModelError


class ReportRequest(BaseModel):
    reportId: str
    generatedAt: str | None = None
    mode: Literal["factual_profile", "uncertainty_report"] = "factual_profile"
    evidenceExcerpts: list[dict[str, Any]] = Field(default_factory=list)
    useFixtures: bool = False


class DraftRequest(BaseModel):
    recipient: str
    evidenceExcerpts: list[dict[str, Any]] = Field(default_factory=list)
    useFixtures: bool = False


class PingResponse(BaseModel):
    status: Literal["ok"]
    response: str
    model: str


app = FastAPI(title="Borrowed Intimacy API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _model() -> OpenAICompatibleTextModel:
    return OpenAICompatibleTextModel(get_settings())


def _generated_at(value: str | None) -> str:
    return value or datetime.now(timezone.utc).isoformat()


@app.get("/api/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {"status": "ok", "llmConfigured": settings.llm_configured}


@app.post("/api/llm/ping", response_model=PingResponse)
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


@app.post("/api/projects/{project_id}/reports")
def create_report(project_id: str, request: ReportRequest) -> dict[str, Any]:
    del project_id
    model = None
    try:
        if not request.useFixtures:
            model = _model()
        return generate_report(
            report_id=request.reportId,
            generated_at=_generated_at(request.generatedAt),
            mode=request.mode,
            evidence_excerpts=request.evidenceExcerpts,
            model=model,
            use_fixtures=request.useFixtures,
        )
    except (ReportGenerationError, TextModelError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        if model is not None:
            model.close()


@app.post("/api/projects/{project_id}/drafts")
def create_draft(project_id: str, request: DraftRequest) -> dict[str, Any]:
    del project_id
    model = None
    try:
        if not request.useFixtures:
            model = _model()
        return generate_communication_draft(
            recipient=request.recipient,
            evidence_excerpts=request.evidenceExcerpts,
            model=model,
            use_fixtures=request.useFixtures,
        )
    except (CommunicationDraftError, TextModelError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        if model is not None:
            model.close()
>>>>>>> 6308a7a (feat: add LLM API integration)
