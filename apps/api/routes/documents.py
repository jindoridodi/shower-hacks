from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from apps.api.schemas.document import (
    ChunkBatchCreate,
    ChunkRead,
    ChunkSearchRead,
    DocumentCreate,
    DocumentRead,
)
from apps.api.services import documents as document_service

router = APIRouter(tags=["documents"])


@router.post("/documents", response_model=DocumentRead)
def create_document(
    payload: DocumentCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> DocumentRead:
    """Store a document. Returns 201, or 200 when the source already has this content hash."""
    document, created = document_service.create_document(
        db,
        source_id=payload.source_id,
        title=payload.title,
        content_type=payload.content_type,
        raw_text=payload.raw_text,
        cleaned_text=payload.cleaned_text,
        sensitivity_status=payload.sensitivity_status.value,
        content_hash=payload.content_hash,
        chunks=[(chunk.chunk_index, chunk.text) for chunk in payload.chunks],
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return DocumentRead.model_validate(document).model_copy(update={"deduplicated": not created})


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentRead:
    return DocumentRead.model_validate(document_service.get_document(db, document_id))


@router.post(
    "/documents/{document_id}/chunks",
    response_model=list[ChunkRead],
    status_code=status.HTTP_201_CREATED,
)
def add_document_chunks(
    document_id: str,
    payload: ChunkBatchCreate,
    db: Session = Depends(get_db),
) -> list[ChunkRead]:
    rows = document_service.add_chunks(
        db,
        document_id,
        [(chunk.chunk_index, chunk.text) for chunk in payload.chunks],
    )
    return [ChunkRead.model_validate(row) for row in rows]


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkRead])
def list_document_chunks(document_id: str, db: Session = Depends(get_db)) -> list[ChunkRead]:
    return [ChunkRead.model_validate(row) for row in document_service.list_chunks(db, document_id)]


@router.get("/search/chunks", response_model=list[ChunkSearchRead])
def search_chunks(
    q: str = Query(min_length=1),
    project_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[ChunkSearchRead]:
    hits = document_service.search_chunks(db, q, project_id=project_id, limit=limit)
    return [ChunkSearchRead.model_validate(hit, from_attributes=True) for hit in hits]
