from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.clock import utc_now
from apps.api.config import repo_root
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import CrawlJob, Document, Source
from apps.api.services.documents import stage_document
from apps.api.services.firecrawl import PublicPageScraper, ScrapedPage, get_public_page_scraper
from apps.api.services.sources import get_source
from apps.api.services.hashing import sha256_text
from apps.api.services.urls import InvalidURL, canonicalize_url

_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"running", "failed"},
    "running": {"succeeded", "failed"},
}


def queue_crawl(db: Session, source_id: str) -> CrawlJob:
    source = get_source(db, source_id)
    now = utc_now()
    job = CrawlJob(
        id=str(uuid4()),
        source_id=source.id,
        status="queued",
        created_at=now,
        updated_at=now,
    )
    try:
        with transaction(db):
            locked = db.get(Source, source.id)
            if locked is None:
                raise APIError(404, "source_not_found", "Source not found")
            active = db.scalar(
                select(CrawlJob.id).where(
                    CrawlJob.source_id == locked.id,
                    CrawlJob.status.in_(("queued", "running")),
                )
            )
            if active is not None:
                raise APIError(
                    409,
                    "crawl_already_active",
                    "This source already has a queued or running crawl",
                )
            locked.status = "queued"
            locked.updated_at = now
            db.add(job)
    except APIError as exc:
        if not _is_active_crawl_conflict(exc):
            raise
        raise APIError(
            409,
            "crawl_already_active",
            "This source already has a queued or running crawl",
        ) from exc
    db.refresh(job)
    return job


def _is_active_crawl_conflict(exc: APIError) -> bool:
    if exc.payload["code"] != "integrity_error":
        return False
    # The partial unique index rejects a second queued/running job for one source.
    return "crawl_jobs" in str(exc.__cause__).lower()


def get_crawl(db: Session, crawl_id: str) -> CrawlJob:
    job = db.get(CrawlJob, crawl_id)
    if job is None:
        raise APIError(404, "crawl_not_found", "Crawl job not found")
    return job


def list_crawls(db: Session, source_id: str) -> list[CrawlJob]:
    source = get_source(db, source_id)
    return list(
        db.scalars(
            select(CrawlJob)
            .where(CrawlJob.source_id == source.id)
            .order_by(CrawlJob.created_at, CrawlJob.id)
        ).all()
    )


def update_crawl_status(
    db: Session,
    crawl_id: str,
    status: str,
    error_message: str | None,
) -> CrawlJob:
    job = get_crawl(db, crawl_id)
    if status not in _TRANSITIONS.get(job.status, set()):
        raise APIError(
            409,
            "invalid_status_transition",
            f"Cannot change crawl status from {job.status} to {status}",
        )

    cleaned_error = error_message.strip() if error_message else None
    if status == "failed" and not cleaned_error:
        raise APIError(422, "error_message_required", "A failed crawl requires an error message")
    if status in {"succeeded", "running"} and cleaned_error:
        raise APIError(
            422,
            "error_message_not_allowed",
            f"A {status} crawl cannot include an error message",
        )

    source = db.get(Source, job.source_id)
    if source is None:
        raise APIError(404, "source_not_found", "Source not found")

    now = utc_now()
    with transaction(db):
        job.status = status
        job.updated_at = now
        source.status = status
        source.updated_at = now
        if status == "running":
            job.started_at = now
        elif status == "failed":
            job.error_message = cleaned_error
            job.completed_at = now
        elif status == "succeeded":
            job.error_message = None
            job.completed_at = now
            source.scraped_at = now
    db.refresh(job)
    return job


def ingest_scraped_page(db: Session, crawl_id: str, page: ScrapedPage) -> Document:
    """Store a scraper result and mark the crawl succeeded.

    Workers should call this after PublicPageScraper.scrape_public_url. The HTTP
    API does not call it, so a missing Firecrawl client cannot fetch pages.
    """
    job = get_crawl(db, crawl_id)
    if job.status in {"succeeded", "failed"}:
        raise APIError(
            409,
            "invalid_status_transition",
            f"Cannot ingest a page for a {job.status} crawl",
        )
    source = get_source(db, job.source_id)
    try:
        canonical = canonicalize_url(page.url)
    except InvalidURL as exc:
        raise APIError(422, "invalid_url", str(exc)) from exc
    if canonical != source.canonical_url:
        raise APIError(
            409,
            "url_mismatch",
            "Scraped URL does not match the source canonical URL",
        )
    markdown = page.markdown.strip()
    if not markdown:
        raise APIError(422, "empty_document", "Scraped page has no markdown text")

    raw_path = _store_raw_markdown(source.id, markdown)
    now = utc_now()
    with transaction(db):
        if job.started_at is None:
            job.started_at = now
        job.status = "running"
        job.updated_at = now
        source.status = "running"
        source.updated_at = now
        document, _created = stage_document(
            db,
            source_id=source.id,
            title=page.title,
            content_type="text/markdown",
            raw_path=raw_path,
            raw_text=page.raw_html,
            cleaned_text=markdown,
            sensitivity_status="unreviewed",
            content_hash=None,
        )
        finished = utc_now()
        job.status = "succeeded"
        job.error_message = None
        job.completed_at = finished
        job.updated_at = finished
        source.status = "succeeded"
        source.scraped_at = finished
        source.updated_at = finished
    db.refresh(document)
    return document


def run_queued_crawl(
    db: Session,
    crawl_id: str,
    scraper: PublicPageScraper | None = None,
) -> Document:
    """Worker entry point: scrape the queued source and persist its schema-backed result."""

    job = get_crawl(db, crawl_id)
    if job.status != "queued":
        raise APIError(409, "invalid_status_transition", "Only queued crawls can be run")
    source = get_source(db, job.source_id)
    update_crawl_status(db, crawl_id, "running", None)
    try:
        page = (scraper or get_public_page_scraper()).scrape_public_url(source.url)
        return ingest_scraped_page(db, crawl_id, page)
    except Exception as error:
        update_crawl_status(db, crawl_id, "failed", str(error))
        raise


def _store_raw_markdown(source_id: str, markdown: str) -> str:
    """Persist raw extraction outside SQLite and return a repo-relative path."""

    digest = sha256_text(markdown)
    relative = Path("data") / "raw" / source_id / f"{digest}.md"
    destination = repo_root() / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(markdown, encoding="utf-8")
    return str(relative)
