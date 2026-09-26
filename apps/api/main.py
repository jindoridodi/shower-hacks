"""Application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from apps.api.routes.discovery import router as discovery_router
from apps.api.routes.enrichment import router as enrichment_router
from apps.api.routes.graph import router as graph_router
from apps.api.routes.projects import router as projects_router
from apps.api.services.discovery.service import DiscoveryService, build_default_service
from apps.api.services.sources.repository import SQLiteSourceRepository


def create_app(
    discovery_service: DiscoveryService | None = None,
    source_repository: SQLiteSourceRepository | None = None,
) -> FastAPI:
    app = FastAPI(title="Borrowed Intimacy API", version="0.1.0")
    app.state.source_repository = source_repository or SQLiteSourceRepository()
    app.state.discovery_service = discovery_service or build_default_service(app.state.source_repository)
    if discovery_service is not None and discovery_service.source_repository is None:
        discovery_service.source_repository = app.state.source_repository

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(discovery_router)
    app.include_router(graph_router)
    app.include_router(enrichment_router)
    app.include_router(projects_router)
    static_directory = Path(__file__).resolve().parent / "static"
    app.mount("/", StaticFiles(directory=static_directory, html=True), name="osint-test-ui")
    return app


app = create_app()
