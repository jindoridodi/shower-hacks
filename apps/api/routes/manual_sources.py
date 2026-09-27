"""OSINT project and manual public-source HTTP endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from apps.api.services.discovery.normalize import normalize_username
from apps.api.services.discovery.models import SavedSource
from apps.api.services.manual_sources.models import (
    ManualSourceCreateRequest,
    ManualSourceList,
    Project,
    ProjectCreateRequest,
)
from apps.api.services.manual_sources.repository import (
    DuplicateSourceError,
    ProjectNotFoundError,
    SourceNotFoundError,
    SQLiteSourceRepository,
)

router = APIRouter(prefix="/api/osint/projects", tags=["osint-projects", "manual-sources"])


def _repository(request: Request) -> SQLiteSourceRepository:
    return request.app.state.source_repository


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_osint_project(request_body: ProjectCreateRequest, request: Request) -> Project:
    return _repository(request).create_project(request_body.name)


@router.get("", response_model=list[Project])
async def list_osint_projects(request: Request) -> list[Project]:
    return _repository(request).list_projects()


@router.post("/{project_id}/sources", response_model=SavedSource, status_code=status.HTTP_201_CREATED)
async def add_manual_source(project_id: str, request_body: ManualSourceCreateRequest, request: Request) -> SavedSource:
    try:
        return _repository(request).add_source(project_id, request_body.username, request_body.url)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except DuplicateSourceError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/{project_id}/sources", response_model=ManualSourceList)
async def list_manual_sources(project_id: str, username: str, request: Request) -> ManualSourceList:
    try:
        return ManualSourceList(sources=_repository(request).list_sources(project_id, normalize_username(username)))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.delete("/{project_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manual_source(project_id: str, source_id: str, request: Request) -> None:
    try:
        _repository(request).delete_source(project_id, source_id)
    except (ProjectNotFoundError, SourceNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
