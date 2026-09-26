from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.clock import utc_now
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import Source
from apps.api.services.projects import get_project
from apps.api.services.urls import InvalidURL, canonicalize_url


def create_source(db: Session, project_id: str, url: str) -> Source:
    get_project(db, project_id)
    try:
        canonical = canonicalize_url(url)
    except InvalidURL as exc:
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
        created_at=now,
        updated_at=now,
    )
    with transaction(db):
        db.add(source)
    db.refresh(source)
    return source


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
