from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from apps.api.clock import utc_now
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import Source
from apps.api.services.projects import get_project
from apps.api.services.discovery.normalize import validate_public_url
from apps.api.services.urls import InvalidURL, canonicalize_url


def create_source(db: Session, project_id: str, url: str) -> Source:
    get_project(db, project_id)
    try:
        validate_public_url(url)
        canonical = canonicalize_url(url)
    except (InvalidURL, ValueError) as exc:
        raise APIError(422, "invalid_url", str(exc)) from exc

    existing = db.scalar(
        select(Source).where(
            Source.project_id == project_id,
            Source.canonical_url == canonical,
        )
    )
    if existing is not None:
        raise APIError(
            409,
            "duplicate_canonical_url",
            f"A source with canonical URL {canonical} already exists in this project",
            existing_id=existing.id,
        )

    now = utc_now()
    source = Source(
        id=str(uuid4()),
        project_id=project_id,
        url=url.strip(),
        canonical_url=canonical,
        status="pending",
        approval_status="pending",
        is_allowlisted=False,
        created_at=now,
        updated_at=now,
    )
    with transaction(db):
        db.add(source)
    db.refresh(source)
    return source


def update_source_approval(db: Session, source_id: str, approval_status: str) -> Source:
    source = get_source(db, source_id)
    if approval_status not in {"approved", "rejected"}:
        raise APIError(422, "invalid_approval_status", "Approval status must be approved or rejected")

    now = utc_now()
    with transaction(db):
        source.approval_status = approval_status
        source.is_allowlisted = approval_status == "approved"
        source.approved_at = now if approval_status == "approved" else None
        source.approval_origin = "manual" if approval_status == "approved" else "rejected"
        source.updated_at = now
    db.refresh(source)
    return source


def require_crawlable_source(db: Session, source_id: str) -> Source:
    source = get_source(db, source_id)
    if source.approval_status != "approved" or not source.is_allowlisted:
        raise APIError(
            409,
            "source_not_approved",
            "This source must be explicitly approved and allowlisted before crawling.",
        )
    return source


def delete_source(db: Session, source_id: str) -> None:
    source = get_source(db, source_id)
    with transaction(db):
        # Let SQLite enforce ON DELETE CASCADE/RESTRICT instead of having the
        # ORM detach child rows whose foreign keys are intentionally non-null.
        db.execute(delete(Source).where(Source.id == source.id))


def get_source(db: Session, source_id: str) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise APIError(404, "source_not_found", "Source not found")
    return source


def list_sources(db: Session, project_id: str) -> list[Source]:
    get_project(db, project_id)
    return list(
        db.scalars(
            select(Source)
            .where(Source.project_id == project_id)
            .order_by(Source.created_at, Source.id)
        ).all()
    )
