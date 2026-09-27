"""Corpus routes that match the team integration paths.

These handlers read and write the migrated corpus database. They do not replace
the OSINT routes already registered under ``/api/projects``.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.errors import APIError
from apps.api.schemas.crawl import CrawlCreate, CrawlRead, CrawlUpdate
from apps.api.schemas.document import ChunkRead
from apps.api.schemas.integration import CorpusDocumentRead, CorpusRead, PersistReportRequest
from apps.api.schemas.report import ReportRead
from apps.api.schemas.source import SourceRead
from apps.api.services import crawls as crawl_service
from apps.api.services import reports as report_service
from apps.api.services.corpus import get_project_corpus
from apps.api.services.projects import get_project
from apps.api.services.report_persistence import persist_generated_report
from apps.api.services.sources import get_source

router = APIRouter(tags=["integration"])


@router.post(
    "/api/projects/{project_id}/crawls",
    response_model=CrawlRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project_crawl(
    project_id: str,
    payload: CrawlCreate,
    db: Session = Depends(get_db),
) -> CrawlRead:
    get_project(db, project_id)
    source = get_source(db, payload.source_id)
    if source.project_id != project_id:
        raise APIError(
            409,
            "source_project_mismatch",
            "Source belongs to a different project than the crawl",
        )
    return CrawlRead.model_validate(crawl_service.queue_crawl(db, payload.source_id))


@router.get("/api/crawls/{crawl_id}", response_model=CrawlRead)
def get_api_crawl(crawl_id: str, db: Session = Depends(get_db)) -> CrawlRead:
    return CrawlRead.model_validate(crawl_service.get_crawl(db, crawl_id))


@router.patch("/api/crawls/{crawl_id}", response_model=CrawlRead)
def update_api_crawl(
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


@router.get("/api/projects/{project_id}/corpus", response_model=CorpusRead)
def get_corpus(project_id: str, db: Session = Depends(get_db)) -> CorpusRead:
    corpus = get_project_corpus(db, project_id)
    return CorpusRead(
        project_id=corpus.project_id,
        sources=[SourceRead.model_validate(source) for source in corpus.sources],
        documents=[
            CorpusDocumentRead(
                id=document.id,
                source_id=document.source_id,
                content_hash=document.content_hash,
                title=document.title,
                sensitivity_status=document.sensitivity_status,
                chunks=[ChunkRead.model_validate(chunk) for chunk in document.chunks],
            )
            for document in corpus.documents
        ],
    )


@router.post("/api/projects/{project_id}/reports/persisted", response_model=ReportRead)
def persist_report(
    project_id: str,
    payload: PersistReportRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> ReportRead:
    report_input, evidence = payload.to_models()
    stored, created = persist_generated_report(db, project_id, report_input, evidence)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return ReportRead.model_validate(stored)


@router.get("/api/reports/{report_id}", response_model=ReportRead)
def get_api_report(report_id: str, db: Session = Depends(get_db)) -> ReportRead:
    return ReportRead.model_validate(report_service.get_report(db, report_id))
