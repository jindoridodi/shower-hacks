from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.clock import utc_now
from apps.api.db import transaction
from apps.api.models import Project, Source
from apps.api.services.sources import create_source
from apps.api.services.urls import canonicalize_url

DEMO_PROJECT_NAME = "Demo"
DEMO_PROJECT_DESCRIPTION = "Local demo project for a manually supplied public URL."
DEMO_SOURCE_URL = "https://example.com/"


@dataclass(frozen=True)
class SeedResult:
    project: Project
    source: Source
    created: bool


def seed_demo(db: Session) -> SeedResult:
    """Create the demo project and example.com source when they are missing."""
    project = db.scalar(select(Project).where(Project.name == DEMO_PROJECT_NAME))
    project_created = project is None
    if project is None:
        now = utc_now()
        project = Project(
            id=str(uuid4()),
            name=DEMO_PROJECT_NAME,
            description=DEMO_PROJECT_DESCRIPTION,
            created_at=now,
            updated_at=now,
        )
        with transaction(db):
            db.add(project)
        db.refresh(project)

    canonical = canonicalize_url(DEMO_SOURCE_URL)
    source = db.scalar(
        select(Source).where(
            Source.project_id == project.id,
            Source.canonical_url == canonical,
        )
    )
    source_created = source is None
    if source is None:
        source = create_source(db, project.id, DEMO_SOURCE_URL)
    return SeedResult(
        project=project,
        source=source,
        created=project_created or source_created,
    )
