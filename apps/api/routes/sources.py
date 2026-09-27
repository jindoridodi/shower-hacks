from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.schemas.crawl import CrawlRead
from apps.api.schemas.source import ProjectSourceCreate, SourceApprovalUpdate, SourceCreate, SourceRead
from apps.api.services import crawls as crawl_service
from apps.api.services import sources as source_service

router = APIRouter(tags=["sources"])


@router.post("/sources", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> SourceRead:
    source = source_service.create_source(db, payload.project_id, payload.url)
    return SourceRead.model_validate(source)


@router.post("/api/projects/{project_id}/sources", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_project_source(
    project_id: str,
    payload: ProjectSourceCreate,
    db: Session = Depends(get_db),
) -> SourceRead:
    return SourceRead.model_validate(source_service.create_source(db, project_id, payload.url))


@router.get("/sources", response_model=list[SourceRead])
def list_sources(
    project_id: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> list[SourceRead]:
    return [SourceRead.model_validate(source) for source in source_service.list_sources(db, project_id)]


@router.get("/api/projects/{project_id}/sources", response_model=list[SourceRead])
def list_project_sources(project_id: str, db: Session = Depends(get_db)) -> list[SourceRead]:
    return [SourceRead.model_validate(source) for source in source_service.list_sources(db, project_id)]


@router.get("/sources/{source_id}", response_model=SourceRead)
def get_source(source_id: str, db: Session = Depends(get_db)) -> SourceRead:
    return SourceRead.model_validate(source_service.get_source(db, source_id))


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db)) -> Response:
    source_service.delete_source(db, source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/api/projects/{project_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_project_source(project_id: str, source_id: str, db: Session = Depends(get_db)) -> Response:
    source = source_service.get_source(db, source_id)
    if source.project_id != project_id:
        from apps.api.errors import APIError

        raise APIError(404, "source_not_found", "Source not found in this project")
    source_service.delete_source(db, source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/sources/{source_id}/approval", response_model=SourceRead)
def set_source_approval(
    source_id: str,
    payload: SourceApprovalUpdate,
    db: Session = Depends(get_db),
) -> SourceRead:
    return SourceRead.model_validate(
        source_service.update_source_approval(db, source_id, payload.approval_status)
    )


@router.patch("/api/projects/{project_id}/sources/{source_id}/approval", response_model=SourceRead)
def set_project_source_approval(
    project_id: str,
    source_id: str,
    payload: SourceApprovalUpdate,
    db: Session = Depends(get_db),
) -> SourceRead:
    source = source_service.get_source(db, source_id)
    if source.project_id != project_id:
        from apps.api.errors import APIError

        raise APIError(404, "source_not_found", "Source not found in this project")
    return SourceRead.model_validate(
        source_service.update_source_approval(db, source_id, payload.approval_status)
    )


@router.post(
    "/sources/{source_id}/queue",
    response_model=CrawlRead,
    status_code=status.HTTP_201_CREATED,
)
def queue_source(source_id: str, db: Session = Depends(get_db)) -> CrawlRead:
    return CrawlRead.model_validate(crawl_service.queue_crawl(db, source_id))


@router.post(
    "/api/projects/{project_id}/sources/{source_id}/queue",
    response_model=CrawlRead,
    status_code=status.HTTP_201_CREATED,
)
def queue_project_source(project_id: str, source_id: str, db: Session = Depends(get_db)) -> CrawlRead:
    source = source_service.get_source(db, source_id)
    if source.project_id != project_id:
        from apps.api.errors import APIError

        raise APIError(404, "source_not_found", "Source not found in this project")
    return CrawlRead.model_validate(crawl_service.queue_crawl(db, source_id))
