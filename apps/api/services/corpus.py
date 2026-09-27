"""Read the stored pages and chunks for one corpus project."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from apps.api.models import Document, Source
from apps.api.services.projects import get_project
from apps.api.services.sources import list_sources


@dataclass(frozen=True)
class ProjectCorpus:
    project_id: str
    sources: list[Source]
    documents: list[Document]


def get_project_corpus(db: Session, project_id: str) -> ProjectCorpus:
    get_project(db, project_id)
    documents = list(
        db.scalars(
            select(Document)
            .join(Source, Document.source_id == Source.id)
            .where(Source.project_id == project_id)
            .options(selectinload(Document.chunks))
            .order_by(Document.created_at, Document.id)
        ).all()
    )
    return ProjectCorpus(
        project_id=project_id,
        sources=list_sources(db, project_id),
        documents=documents,
    )
