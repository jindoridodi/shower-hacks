from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.clock import utc_now
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import Project


def create_project(db: Session, name: str, description: str | None) -> Project:
    now = utc_now()
    project = Project(
        id=str(uuid4()),
        name=name,
        description=description,
        created_at=now,
        updated_at=now,
    )
    with transaction(db):
        db.add(project)
    db.refresh(project)
    return project


def get_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise APIError(404, "project_not_found", "Project not found")
    return project
