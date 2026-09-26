from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.schemas.crawl import CrawlCreate, CrawlRead, CrawlUpdate
from apps.api.services import crawls as crawl_service

router = APIRouter(tags=["crawls"])


@router.post("/crawls", response_model=CrawlRead, status_code=status.HTTP_201_CREATED)
def create_crawl(payload: CrawlCreate, db: Session = Depends(get_db)) -> CrawlRead:
    return CrawlRead.model_validate(crawl_service.queue_crawl(db, payload.source_id))


@router.get("/crawls", response_model=list[CrawlRead])
def list_crawls(
    source_id: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> list[CrawlRead]:
    return [CrawlRead.model_validate(job) for job in crawl_service.list_crawls(db, source_id)]


@router.get("/crawls/{crawl_id}", response_model=CrawlRead)
def get_crawl(crawl_id: str, db: Session = Depends(get_db)) -> CrawlRead:
    return CrawlRead.model_validate(crawl_service.get_crawl(db, crawl_id))


@router.patch("/crawls/{crawl_id}", response_model=CrawlRead)
def update_crawl(
    crawl_id: str,
    payload: CrawlUpdate,
    db: Session = Depends(get_db),
) -> CrawlRead:
    job = crawl_service.update_crawl_status(
        db,
        crawl_id,
        payload.status.value,
        payload.error_message,
    )
    return CrawlRead.model_validate(job)
