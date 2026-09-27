from pathlib import Path
from contextlib import asynccontextmanager

from starlette.concurrency import run_in_threadpool

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.config import Settings, get_settings
from apps.api.services.embeddings import EmbeddingProvider, prepare_embeddings
from apps.api.db import apply_migrations, make_engine, make_session_factory
from apps.api.dependencies import get_db
from apps.api.errors import APIError
from apps.api.routes import crawls, documents, generation, instagram, integration, projects, reports, sources
from apps.api.routes.discovery import router as discovery_router
from apps.api.routes.graph import router as graph_router
from apps.api.routes.manual_sources import router as manual_sources_router
from apps.api.services.discovery.service import DiscoveryService, build_default_service
from apps.api.services.manual_sources.repository import SQLiteSourceRepository


def create_app(
    database_path: Path | None = None,
    discovery_service: DiscoveryService | None = None,
    source_repository: SQLiteSourceRepository | None = None,
    settings: Settings | None = None,
    embedding_provider: EmbeddingProvider | None = None,
) -> FastAPI:
    current_settings = settings or get_settings()
    path = database_path or current_settings.database_path
    apply_migrations(path)
    engine = make_engine(path)
    @asynccontextmanager
    async def lifespan(application):
        def initialize():
            with application.state.session_factory() as db:
                application.state.embeddings_prepared = prepare_embeddings(db)
        await run_in_threadpool(initialize)
        yield

    app = FastAPI(
        lifespan=lifespan,
        title="freakypeeky API",
        version="0.1.0",
        summary="Source, crawl, document, discovery, and evidence API",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.engine = engine
    app.state.database_path = path
    app.state.session_factory = make_session_factory(engine)
    app.state.session_factory.configure(info={
        "embedding_settings": current_settings,
        "embedding_provider": embedding_provider,
    })
    app.state.source_repository = source_repository or SQLiteSourceRepository()
    app.state.discovery_service = discovery_service or build_default_service(app.state.source_repository)
    if discovery_service is not None and discovery_service.source_repository is None:
        discovery_service.source_repository = app.state.source_repository

    app.include_router(projects.router)
    app.include_router(sources.router)
    app.include_router(crawls.router)
    app.include_router(instagram.router)
    app.include_router(documents.router)
    app.include_router(reports.router)
    app.include_router(integration.router)
    app.include_router(generation.router)
    app.include_router(discovery_router)
    app.include_router(graph_router)
    app.include_router(manual_sources_router)
    _register_handlers(app)

    @app.get("/health", tags=["health"])
    def health(db: Session = Depends(get_db)) -> dict[str, str]:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/api/health", tags=["health"])
    def api_health(db: Session = Depends(get_db)) -> dict[str, object]:
        settings = get_settings()
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "ok",
            "llmConfigured": settings.llm_configured,
            "firecrawlConfigured": bool(settings.firecrawl_api_key),
            "crawlWorkerCommand": "python -m workers.crawl_worker --once",
        }

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
