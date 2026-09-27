"""Project-scoped, generation-safe evidence retrieval.

This is the boundary between stored crawl output and generation services.  It
never accepts browser-provided excerpts: callers supply a project ID and receive
only chunks from documents that completed sensitivity inspection with ``clear``
status.  Redacted content is intentionally excluded from prompts so its
remaining text cannot be mistaken for an unaltered source quotation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.errors import APIError
from apps.api.models import Document, DocumentChunk, Project, Source


@dataclass(frozen=True)
class EvidenceExcerpt:
    sourceId: str
    sourceTitle: str | None
    sourceUrl: str
    text: str
    sensitivityStatus: str = "safe"

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


def list_safe_excerpts(
    db: Session,
    project_id: str,
    *,
    limit: int = 50,
) -> list[EvidenceExcerpt]:
    """Return attributable prompt-safe chunks from one project.

    ``clear`` is the only stored sensitivity status eligible for generation.
    The outward ``safe`` value is the generation contract and deliberately does
    not expose internal review states to model-facing callers.
    """
    if db.get(Project, project_id) is None:
        raise APIError(404, "project_not_found", "Project not found")
    if limit < 1 or limit > 200:
        raise APIError(422, "invalid_evidence_limit", "Evidence limit must be between 1 and 200")

    rows = db.execute(
        select(DocumentChunk, Document, Source)
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
        .where(
            Source.project_id == project_id,
            Document.sensitivity_status == "clear",
        )
        .order_by(Source.created_at, Document.created_at, DocumentChunk.chunk_index)
        .limit(limit)
    ).all()

    return [
        EvidenceExcerpt(
            sourceId=source.id,
            sourceTitle=document.title,
            sourceUrl=source.canonical_url,
            text=chunk.text,
        )
        for chunk, document, source in rows
    ]
