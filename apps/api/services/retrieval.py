"""Retrieve chunks through the backend's persistent SQLite FTS5 index."""
from sqlalchemy.orm import Session

from .documents import ChunkHit, search_chunks as document_search_chunks


def search_chunks(
    db: Session, query: str, *, project_id: str | None = None, limit: int = 20
) -> list[ChunkHit]:
    return document_search_chunks(db, query, project_id=project_id, limit=limit)
