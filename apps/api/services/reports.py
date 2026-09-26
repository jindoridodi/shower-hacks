from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from apps.api.clock import utc_now
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import ClaimSource, Report, ReportClaim, Source
from apps.api.schemas.report import ClaimSourceCreate
from apps.api.services.projects import get_project


def create_report(db: Session, project_id: str, title: str) -> Report:
    get_project(db, project_id)
    now = utc_now()
    report = Report(
        id=str(uuid4()),
        project_id=project_id,
        title=title,
        created_at=now,
        updated_at=now,
    )
    with transaction(db):
        db.add(report)
    return _load_report(db, report.id)


def get_report(db: Session, report_id: str) -> Report:
    return _load_report(db, report_id)


def create_claim(
    db: Session,
    report_id: str,
    claim_text: str,
    links: list[ClaimSourceCreate],
) -> ReportClaim:
    report = db.get(Report, report_id)
    if report is None:
        raise APIError(404, "report_not_found", "Report not found")
    resolved: list[tuple[Source, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in links:
        key = (item.source_id, item.excerpt)
        if key in seen:
            raise APIError(
                409,
                "duplicate_claim_source",
                "This excerpt is already linked to the claim",
            )
        seen.add(key)
        resolved.append(_resolve_source(db, report, item))
    position = db.scalar(
        select(func.count()).select_from(ReportClaim).where(ReportClaim.report_id == report.id)
    )
    now = utc_now()
    claim = ReportClaim(
        id=str(uuid4()),
        report_id=report.id,
        claim_text=claim_text,
        position=int(position or 0),
        created_at=now,
    )
    with transaction(db):
        db.add(claim)
        db.flush()
        for source, excerpt in resolved:
            _add_link(db, claim, source, excerpt, now)
    return _load_claim(db, claim.id)


def add_claim_source(
    db: Session,
    claim_id: str,
    source_id: str,
    excerpt: str,
) -> ReportClaim:
    claim = db.get(ReportClaim, claim_id)
    if claim is None:
        raise APIError(404, "claim_not_found", "Claim not found")
    report = db.get(Report, claim.report_id)
    if report is None:
        raise APIError(404, "report_not_found", "Report not found")
    source = _source_for_report(db, report, source_id)
    _reject_duplicate_excerpt(db, claim.id, source.id, excerpt)
    with transaction(db):
        _add_link(db, claim, source, excerpt, utc_now())
    return _load_claim(db, claim.id)


def _resolve_source(
    db: Session,
    report: Report,
    item: ClaimSourceCreate,
) -> tuple[Source, str]:
    return _source_for_report(db, report, item.source_id), item.excerpt


def _source_for_report(db: Session, report: Report, source_id: str) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise APIError(404, "source_not_found", "Source not found")
    if source.project_id != report.project_id:
        raise APIError(
            409,
            "source_project_mismatch",
            "Source belongs to a different project than the report",
        )
    return source


def _reject_duplicate_excerpt(
    db: Session,
    claim_id: str,
    source_id: str,
    excerpt: str,
) -> None:
    existing = db.scalar(
        select(ClaimSource.id).where(
            ClaimSource.claim_id == claim_id,
            ClaimSource.source_id == source_id,
            ClaimSource.excerpt == excerpt,
        )
    )
    if existing is not None:
        raise APIError(
            409,
            "duplicate_claim_source",
            "This excerpt is already linked to the claim",
        )


def _add_link(
    db: Session,
    claim: ReportClaim,
    source: Source,
    excerpt: str,
    created_at: str,
) -> ClaimSource:
    link = ClaimSource(
        id=str(uuid4()),
        claim_id=claim.id,
        source_id=source.id,
        excerpt=excerpt,
        created_at=created_at,
    )
    db.add(link)
    return link


def _load_report(db: Session, report_id: str) -> Report:
    report = db.scalar(
        select(Report)
        .where(Report.id == report_id)
        .options(selectinload(Report.claims).selectinload(ReportClaim.sources))
    )
    if report is None:
        raise APIError(404, "report_not_found", "Report not found")
    return report


def _load_claim(db: Session, claim_id: str) -> ReportClaim:
    claim = db.scalar(
        select(ReportClaim)
        .where(ReportClaim.id == claim_id)
        .options(selectinload(ReportClaim.sources))
    )
    if claim is None:
        raise APIError(404, "claim_not_found", "Claim not found")
    return claim

