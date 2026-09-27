from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from apps.api.clock import utc_now
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import ClaimSource, Report, ReportClaim, Source
from apps.api.schemas.report import ClaimSourceCreate
from apps.api.services.projects import get_project


def create_report(
    db: Session,
    project_id: str,
    title: str,
    *,
    report_id: str | None = None,
) -> Report:
    get_project(db, project_id)
    now = utc_now()
    report = Report(
        id=report_id or str(uuid4()),
        project_id=project_id,
        title=title,
        created_at=now,
        updated_at=now,
    )
    with transaction(db):
        db.add(report)
    return _load_report(db, report.id)


def persist_generated_report(
    db: Session,
    *,
    project_id: str,
    generated_report: Mapping[str, Any],
    evidence_excerpts: Sequence[Mapping[str, Any]],
) -> Report:
    """Persist validated generated claims with their stored evidence excerpts."""
    report_id = generated_report.get("id")
    title = generated_report.get("title")
    if not isinstance(report_id, str) or not isinstance(title, str):
        raise APIError(422, "invalid_generated_report", "Generated report metadata is invalid")

    excerpts_by_source: dict[str, list[str]] = {}
    for excerpt in evidence_excerpts:
        source_id = excerpt.get("sourceId")
        text = excerpt.get("text")
        if not isinstance(source_id, str) or not isinstance(text, str):
            continue
        excerpts_by_source.setdefault(source_id, []).append(text)
    prepared_claims: list[tuple[str, list[ClaimSourceCreate]]] = []
    for claim in generated_report.get("claims", []):
        if not isinstance(claim, Mapping):
            raise APIError(422, "invalid_generated_report", "Generated claims must be objects")
        claim_text = claim.get("text")
        source_ids = claim.get("sourceIds")
        if not isinstance(claim_text, str) or not isinstance(source_ids, list):
            raise APIError(422, "invalid_generated_report", "Generated claim data is invalid")
        if not all(isinstance(source_id, str) and source_id in excerpts_by_source for source_id in source_ids):
            raise APIError(422, "invalid_generated_report", "Generated claim cited unavailable evidence")
        links = [
            ClaimSourceCreate(source_id=source_id, excerpt=excerpt)
            for source_id in source_ids
            for excerpt in dict.fromkeys(excerpts_by_source[source_id])
        ]
        prepared_claims.append((claim_text, links))

    now = utc_now()
    report = Report(
        id=report_id,
        project_id=project_id,
        title=title,
        created_at=now,
        updated_at=now,
    )
    resolved_claims: list[tuple[str, list[tuple[Source, str]]]] = []
    for claim_text, links in prepared_claims:
        resolved_claims.append(
            (claim_text, [_resolve_source(db, report, link) for link in links])
        )

    with transaction(db):
        db.add(report)
        for position, (claim_text, resolved_links) in enumerate(resolved_claims):
            claim = ReportClaim(
                id=str(uuid4()),
                report_id=report.id,
                claim_text=claim_text,
                position=position,
                created_at=now,
            )
            db.add(claim)
            for source, excerpt in resolved_links:
                _add_link(db, claim, source, excerpt, now)
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
    report_id_value = report.id
    claim_id = _insert_claim_with_unique_position(
        db,
        report_id=report_id_value,
        claim_text=claim_text,
        resolved=resolved,
    )
    return _load_claim(db, claim_id)


def _insert_claim_with_unique_position(
    db: Session,
    report_id: str,
    claim_text: str,
    resolved: list[tuple[Source, str]],
) -> str:
    """Insert a claim at the next position, retrying if another writer took it."""
    for _attempt in range(8):
        now = utc_now()
        claim = ReportClaim(
            id=str(uuid4()),
            report_id=report_id,
            claim_text=claim_text,
            position=0,
            created_at=now,
        )
        try:
            with transaction(db):
                position = db.scalar(
                    select(func.coalesce(func.max(ReportClaim.position), -1) + 1).where(
                        ReportClaim.report_id == report_id
                    )
                )
                claim.position = int(position or 0)
                db.add(claim)
                db.flush()
                for source, excerpt in resolved:
                    _add_link(db, claim, source, excerpt, now)
            return claim.id
        except APIError as exc:
            if not _is_claim_position_conflict(exc):
                raise
    raise APIError(
        409,
        "integrity_error",
        "Could not assign a unique claim position.",
    )


def _is_claim_position_conflict(exc: APIError) -> bool:
    if exc.payload["code"] != "integrity_error":
        return False
    return "report_claims" in str(exc.__cause__).lower()


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
