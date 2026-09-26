from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from apps.api.clock import utc_now
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import Document, DocumentChunk, Project
from apps.api.services.hashing import sha256_text
from apps.api.services.sources import get_source

_FTS_TOKEN = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class ChunkHit:
    id: str
    document_id: str
    source_id: str
    chunk_index: int
    text: str


def content_digest(*, cleaned_text: str | None, raw_text: str | None) -> str:
    # Hash cleaned text when it exists so a raw-markup change does not store
    # a second document after the cleaned body stays the same.
    if cleaned_text:
        basis = cleaned_text
    elif raw_text:
        basis = raw_text
    else:
        raise APIError(422, "empty_document", "A document needs cleaned_text or raw_text")
    return sha256_text(basis)


def stage_document(
    db: Session,
    *,
    source_id: str,
    title: str | None,
    content_type: str | None,
    raw_text: str | None,
    cleaned_text: str | None,
    sensitivity_status: str,
    content_hash: str | None,
    processing_metadata: dict[str, str] | None = None,
    sensitivity_findings: list[dict[str, str]] | None = None,
    metadata_findings: list[dict[str, str]] | None = None,
) -> tuple[Document, bool]:
    source = get_source(db, source_id)
    digest = content_digest(cleaned_text=cleaned_text, raw_text=raw_text)
    if content_hash is not None and content_hash != digest:
        raise APIError(
            422,
            "content_hash_mismatch",
            "content_hash does not match the document text",
        )

    existing = db.scalar(
        select(Document).where(
            Document.source_id == source.id,
            Document.content_hash == digest,
        )
    )
    if existing is not None:
        # Re-seeing this content is the source's latest snapshot, even when the
        # document row already exists.
        source.content_hash = digest
        source.updated_at = utc_now()
        return existing, False

    now = utc_now()
    document = Document(
        id=_new_id(),
        source_id=source.id,
        content_hash=digest,
        title=title,
        content_type=content_type,
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        sensitivity_status=sensitivity_status,
        processing_metadata=processing_metadata or {},
        sensitivity_findings=sensitivity_findings or [],
        metadata_findings=metadata_findings or [],
        created_at=now,
        updated_at=now,
    )
    source.content_hash = digest
    source.updated_at = now
    db.add(document)
    db.flush()
    return document, True


def create_document(
    db: Session,
    *,
    source_id: str,
    title: str | None,
    content_type: str | None,
    raw_text: str | None,
    cleaned_text: str | None,
    sensitivity_status: str,
    content_hash: str | None,
    chunks: list[tuple[int, str]],
) -> tuple[Document, bool]:
    with transaction(db):
        document, created = stage_document(
            db,
            source_id=source_id,
            title=title,
            content_type=content_type,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            sensitivity_status=sensitivity_status,
            content_hash=content_hash,
        )
        if created and chunks:
            stage_chunks(db, document, chunks)
    db.refresh(document)
    return document, created


def stage_chunks(
    db: Session,
    document: Document,
    chunks: list[tuple[int, str]],
) -> list[DocumentChunk]:
    indexes = [index for index, _body in chunks]
    if len(indexes) != len(set(indexes)):
        raise APIError(
            422,
            "duplicate_chunk_index",
            "Chunk indexes in the request must be unique",
        )
    existing = set(
        db.scalars(
            select(DocumentChunk.chunk_index).where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.chunk_index.in_(indexes),
            )
        ).all()
    )
    if existing:
        listed = ", ".join(str(index) for index in sorted(existing))
        raise APIError(409, "duplicate_chunk_index", f"Chunk indexes already exist: {listed}")

    now = utc_now()
    rows: list[DocumentChunk] = []
    for index, body in chunks:
        row = DocumentChunk(
            id=_new_id(),
            document_id=document.id,
            chunk_index=index,
            text=body,
            created_at=now,
        )
        db.add(row)
        rows.append(row)
    return rows


def add_chunks(
    db: Session,
    document_id: str,
    chunks: list[tuple[int, str]],
) -> list[DocumentChunk]:
    document = get_document(db, document_id)
    with transaction(db):
        rows = stage_chunks(db, document, chunks)
    for row in rows:
        db.refresh(row)
    return rows


def get_document(db: Session, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise APIError(404, "document_not_found", "Document not found")
    return document


def list_chunks(db: Session, document_id: str) -> list[DocumentChunk]:
    get_document(db, document_id)
    return list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        ).all()
    )


def search_chunks(
    db: Session,
    query: str,
    *,
    project_id: str | None = None,
    limit: int = 20,
) -> list[ChunkHit]:
    if project_id is not None and db.get(Project, project_id) is None:
        raise APIError(404, "project_not_found", "Project not found")

    fts_query = _fts_query(query)
    project_clause = ""
    params: dict[str, object] = {"query": fts_query, "limit": limit}
    if project_id is not None:
        project_clause = "AND s.project_id = :project_id"
        params["project_id"] = project_id

    statement = text(
        f"""
        SELECT
            c.id AS id,
            c.document_id AS document_id,
            c.chunk_index AS chunk_index,
            c.text AS text,
            d.source_id AS source_id
        FROM document_chunks_fts
        JOIN document_chunks AS c ON c.id = document_chunks_fts.chunk_id
        JOIN documents AS d ON d.id = c.document_id
        JOIN sources AS s ON s.id = d.source_id
        WHERE document_chunks_fts MATCH :query
          {project_clause}
        ORDER BY bm25(document_chunks_fts)
        LIMIT :limit
        """
    )
    try:
        rows = db.execute(statement, params).mappings().all()
    except OperationalError as exc:
        raise APIError(400, "invalid_search", "Search query could not be executed") from exc
    return [
        ChunkHit(
            id=row["id"],
            document_id=row["document_id"],
            source_id=row["source_id"],
            chunk_index=row["chunk_index"],
            text=row["text"],
        )
        for row in rows
    ]


def _fts_query(raw: str) -> str:
    tokens = _FTS_TOKEN.findall(raw)
    if not tokens:
        raise APIError(422, "invalid_search", "Search query needs at least one word")
    return " AND ".join(f'"{token}"' for token in tokens)


def _new_id() -> str:
    return str(uuid4())
