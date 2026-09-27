"""Store a validated generated report and the excerpts that support it."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from apps.api.clock import utc_now
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import ClaimSource, Document, Report, ReportClaim, Source
from apps.api.services.projects import get_project
from apps.api.services.reports import _add_link, _load_report

_CLAIM_TYPES = {"observed", "inferred", "uncertain", "unknown"}
_CITED_TYPES = {"observed", "inferred", "uncertain"}
_KNOWN_SENSITIVITY = {"safe", "clear", "unreviewed", "sensitive", "restricted", "redacted"}
_BLOCKED_SENSITIVITY = {"sensitive", "restricted", "redacted"}
_BLOCKED_DOCUMENT_SENSITIVITY = {"sensitive", "redacted"}


@dataclass(frozen=True)
class EvidenceExcerpt:
    source_id: str
    text: str
    sensitivity_status: str


@dataclass(frozen=True)
class GeneratedClaim:
    id: str
    text: str
    claim_type: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class GeneratedReport:
    id: str
    title: str
    claims: tuple[GeneratedClaim, ...]
    unknowns: tuple[str, ...] = ()


def persist_generated_report(
    db: Session,
    project_id: str,
    report: GeneratedReport,
    evidence: list[EvidenceExcerpt],
) -> tuple[Report, bool]:
    """Create or replace a report and its citations in one transaction.

    A failed check rolls the transaction back, so a rejected excerpt does not
    leave a report, claim, or claim-source row behind.
    """
    claims = _claims_with_unknowns(report)
    _validate_claim_shape(claims)
    evidence_by_source = _index_evidence(evidence)
    with transaction(db):
        get_project(db, project_id)
        links = _resolve_links(db, project_id, claims, evidence_by_source)
        created = _write_report(db, project_id, report, claims, links)
    return _load_report(db, report.id), created


def _claims_with_unknowns(report: GeneratedReport) -> list[GeneratedClaim]:
    claims = list(report.claims)
    seen_text = {claim.text for claim in claims}
    for index, unknown in enumerate(report.unknowns):
        if unknown in seen_text:
            continue
        claims.append(
            GeneratedClaim(
                id=f"{report.id}:unknown:{index}",
                text=unknown,
                claim_type="unknown",
                source_ids=(),
            )
        )
        seen_text.add(unknown)
    return claims


def _validate_claim_shape(claims: list[GeneratedClaim]) -> None:
    seen_ids: set[str] = set()
    for claim in claims:
        if claim.id in seen_ids:
            raise APIError(422, "duplicate_claim_id", "A report cannot contain the same claim id twice")
        seen_ids.add(claim.id)
        if claim.claim_type not in _CLAIM_TYPES:
            raise APIError(422, "invalid_claim_type", "claim_type is not supported")
        if not claim.text.strip():
            raise APIError(422, "empty_claim", "A claim needs text")
        if claim.claim_type in _CITED_TYPES and not claim.source_ids:
            raise APIError(
                422,
                "claim_requires_evidence",
                "A source-backed claim needs at least one source id",
            )
        if len(claim.source_ids) != len(set(claim.source_ids)):
            raise APIError(422, "duplicate_claim_source", "A claim cites the same source twice")


def _index_evidence(evidence: list[EvidenceExcerpt]) -> dict[str, EvidenceExcerpt]:
    indexed: dict[str, EvidenceExcerpt] = {}
    for excerpt in evidence:
        if excerpt.sensitivity_status not in _KNOWN_SENSITIVITY:
            raise APIError(
                422,
                "invalid_sensitivity",
                "sensitivity_status is not supported",
            )
        if not excerpt.text.strip():
            raise APIError(422, "empty_excerpt", "An evidence excerpt needs text")
        previous = indexed.get(excerpt.source_id)
        if previous is not None and previous.text != excerpt.text:
            raise APIError(
                422,
                "ambiguous_evidence",
                "The same source was given two different excerpts",
            )
        indexed[excerpt.source_id] = excerpt
    return indexed


def _resolve_links(
    db: Session,
    project_id: str,
    claims: list[GeneratedClaim],
    evidence_by_source: dict[str, EvidenceExcerpt],
) -> dict[str, list[tuple[Source, str]]]:
    resolved: dict[str, list[tuple[Source, str]]] = {}
    for claim in claims:
        links: list[tuple[Source, str]] = []
        for source_id in claim.source_ids:
            excerpt = evidence_by_source.get(source_id)
            if excerpt is None:
                raise APIError(
                    409,
                    "unavailable_evidence",
                    "A cited source has no evidence excerpt",
                )
            if excerpt.sensitivity_status in _BLOCKED_SENSITIVITY:
                raise APIError(
                    409,
                    "sensitive_evidence",
                    "Sensitive evidence cannot be stored as a citation",
                )
            source = db.get(Source, source_id)
            if source is None:
                raise APIError(404, "source_not_found", "Source not found")
            if source.project_id != project_id:
                raise APIError(
                    409,
                    "source_project_mismatch",
                    "Source belongs to a different project than the report",
                )
            _reject_sensitive_document(db, source, excerpt.text)
            links.append((source, excerpt.text))
        resolved[claim.id] = links
    return resolved


def _reject_sensitive_document(db: Session, source: Source, excerpt: str) -> None:
    documents = db.scalars(select(Document).where(Document.source_id == source.id)).all()
    for document in documents:
        if document.sensitivity_status not in _BLOCKED_DOCUMENT_SENSITIVITY:
            continue
        body = document.cleaned_text or document.raw_text or ""
        if excerpt in body or document.content_hash == source.content_hash:
            raise APIError(
                409,
                "sensitive_evidence",
                "Sensitive evidence cannot be stored as a citation",
            )


def _write_report(
    db: Session,
    project_id: str,
    report: GeneratedReport,
    claims: list[GeneratedClaim],
    links: dict[str, list[tuple[Source, str]]],
) -> bool:
    now = utc_now()
    existing = db.get(Report, report.id)
    created = existing is None
    if existing is None:
        existing = Report(
            id=report.id,
            project_id=project_id,
            title=report.title,
            created_at=now,
            updated_at=now,
        )
        db.add(existing)
        db.flush()
    else:
        if existing.project_id != project_id:
            raise APIError(
                409,
                "report_project_mismatch",
                "Report belongs to a different project",
            )
        existing.title = report.title
        existing.updated_at = now
        stored_claims = db.scalars(
            select(ReportClaim).where(ReportClaim.report_id == existing.id)
        ).all()
        stored_ids = [stored.id for stored in stored_claims]
        if stored_ids:
            # Core deletes follow the foreign keys. ORM delete would null
            # claim_id and violate the NOT NULL constraint.
            db.execute(delete(ClaimSource).where(ClaimSource.claim_id.in_(stored_ids)))
            db.execute(delete(ReportClaim).where(ReportClaim.id.in_(stored_ids)))
            for stored in stored_claims:
                db.expunge(stored)
        db.flush()

    for position, claim in enumerate(claims):
        row = ReportClaim(
            id=claim.id,
            report_id=existing.id,
            claim_text=claim.text,
            position=position,
            created_at=now,
        )
        db.add(row)
        db.flush()
        seen_excerpts: set[tuple[str, str]] = set()
        for source, excerpt in links[claim.id]:
            key = (source.id, excerpt)
            if key in seen_excerpts:
                continue
            seen_excerpts.add(key)
            _add_link(db, row, source, excerpt, now)
    return created
