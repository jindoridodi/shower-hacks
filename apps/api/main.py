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
