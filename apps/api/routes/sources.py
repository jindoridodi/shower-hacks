from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.schemas.crawl import CrawlRead
from apps.api.schemas.source import SourceCreate, SourceRead
from apps.api.services import crawls as crawl_service
from apps.api.services import sources as source_service

router = APIRouter(tags=["sources"])


@router.post("/sources", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> SourceRead:
    source = source_service.create_source(db, payload.project_id, payload.url)
    return SourceRead.model_validate(source)


@router.get("/sources", response_model=list[SourceRead])
def list_sources(
    project_id: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> list[SourceRead]:
    return [SourceRead.model_validate(source) for source in source_service.list_sources(db, project_id)]


@router.get("/sources/{source_id}", response_model=SourceRead)
def get_source(source_id: str, db: Session = Depends(get_db)) -> SourceRead:
    return SourceRead.model_validate(source_service.get_source(db, source_id))


@router.post(
    "/sources/{source_id}/queue",
    response_model=CrawlRead,
    status_code=status.HTTP_201_CREATED,
)
def queue_source(source_id: str, db: Session = Depends(get_db)) -> CrawlRead:
    return CrawlRead.model_validate(crawl_service.queue_crawl(db, source_id))
