"""Optional local BGE inference, startup backfill, and cosine retrieval.

No ML libraries are imported when embeddings are disabled. Vectors are tied to
model revision and exact chunk text; no FTS or rank fusion is performed here.
"""
from __future__ import annotations

import math
from functools import lru_cache
from threading import Lock
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from apps.api.clock import utc_now
from apps.api.config import Settings, get_settings
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import ChunkEmbedding, Document, DocumentChunk, Source
from apps.api.services.hashing import sha256_text

QUERY_PREFIX = 'Represent this sentence for searching relevant passages: '


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


def unit_vector(values, dimensions: int) -> list[float]:
    """Validate numeric, finite, nonzero vectors before storing or scoring."""
    if not isinstance(values, (list, tuple)) or len(values) != dimensions:
        raise APIError(503, 'invalid_embedding', 'Embedding dimensions do not match the model')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
        raise APIError(503, 'invalid_embedding', 'Embedding values must be finite numbers')
    vector = [float(v) for v in values]
    if not all(math.isfinite(v) for v in vector):
        raise APIError(503, 'invalid_embedding', 'Embedding values must be finite numbers')
    norm = math.hypot(*vector)
    if not math.isfinite(norm) or norm == 0:
        raise APIError(503, 'invalid_embedding', 'Embedding vector must have nonzero finite length')
    return [v / norm for v in vector]


class BGEEmbedder:
    def __init__(self, settings: Settings):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise APIError(503, 'embedding_dependency_missing',
                           'Install the embeddings extra: pip install -e ".[embeddings]"') from None
        try:
            self.model = SentenceTransformer(
                settings.embedding_model, revision=settings.embedding_model_revision,
                device='cpu', cache_folder=settings.embedding_cache_dir,
                trust_remote_code=False,
            )
        except Exception:
            raise APIError(503, 'embedding_model_unavailable',
                           'BGE model could not be loaded; check model cache and network access') from None
        self.dimensions = self.model.get_sentence_embedding_dimension()
        self.batch_size = settings.embedding_batch_size
        self.lock = Lock()

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(t, str) or not t.strip() for t in texts):
            raise APIError(422, 'empty_embedding_input', 'Embedding input must contain text')
        with self.lock:
            # encode() otherwise silently truncates. Count special/prompt tokens too.
            lengths = self.model.tokenizer(texts, truncation=False, padding=False,
                                           return_length=True, verbose=False)['length']
            if any(n > self.model.max_seq_length for n in lengths):
                raise APIError(422, 'embedding_input_too_long',
                               'Input exceeds the embedding token limit; use smaller chunks or query')
            try:
                vectors = self.model.encode(texts, batch_size=self.batch_size,
                                            normalize_embeddings=True, show_progress_bar=False).tolist()
            except Exception:
                raise APIError(503, 'embedding_inference_failed', 'BGE embedding calculation failed') from None
        return [unit_vector(v, self.dimensions) for v in vectors]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([QUERY_PREFIX + text])[0]


@lru_cache(maxsize=1)
def _cached_provider(model: str, revision: str, cache_dir: str | None, batch_size: int):
    return BGEEmbedder(Settings(embedding_model=model, embedding_model_revision=revision,
                                embedding_cache_dir=cache_dir, embedding_batch_size=batch_size))


def embedding_settings(db: Session) -> Settings:
    return db.info.get('embedding_settings') or get_settings()


def get_provider(db: Session) -> EmbeddingProvider:
    settings = embedding_settings(db)
    if not settings.embeddings_enabled:
        raise APIError(503, 'embeddings_disabled', 'Embeddings are disabled')
    if db.info.get('embedding_provider') is not None:
        return db.info['embedding_provider']
    return _cached_provider(settings.embedding_model, settings.embedding_model_revision,
                            settings.embedding_cache_dir, settings.embedding_batch_size)


def _current(row: ChunkEmbedding | None, chunk: DocumentChunk, settings: Settings, dimensions: int) -> bool:
    return (row is not None and row.model_name == settings.embedding_model
            and row.model_revision == settings.embedding_model_revision
            and row.dimensions == dimensions and row.text_hash == sha256_text(chunk.text))


def _reusable(row, chunk, settings, dimensions):
    if not _current(row, chunk, settings, dimensions):
        return False
    try:
        unit_vector(row.vector_json, dimensions)
    except APIError:
        return False
    return True


def stage_embeddings(db: Session, chunks: list[DocumentChunk]) -> int:
    """Stage vectors in the caller's transaction; disabled mode is a no-op."""
    settings = embedding_settings(db)
    if not settings.embeddings_enabled or not chunks:
        return 0
    provider = get_provider(db)
    pending = [c for c in chunks if not _reusable(db.get(ChunkEmbedding, c.id), c, settings, provider.dimensions)]
    for start in range(0, len(pending), settings.embedding_batch_size):
        batch = pending[start:start + settings.embedding_batch_size]
        # Detect stale ORM data after text edits in this same transaction.
        texts = [c.text for c in batch]
        vectors = provider.embed_documents(texts)
        if len(vectors) != len(batch):
            raise APIError(503, 'invalid_embedding', 'Model returned the wrong number of embeddings')
        for chunk, vector in zip(batch, vectors):
            values = dict(chunk_id=chunk.id, model_name=settings.embedding_model,
                          model_revision=settings.embedding_model_revision, dimensions=provider.dimensions,
                          text_hash=sha256_text(chunk.text), vector_json=unit_vector(vector, provider.dimensions),
                          created_at=utc_now())
            statement = insert(ChunkEmbedding).values(**values)
            db.execute(statement.on_conflict_do_update(index_elements=['chunk_id'], set_=values))
    # SQL upserts must not leave previously loaded ORM rows stale.
    for row in list(db.identity_map.values()):
        if isinstance(row, ChunkEmbedding):
            db.expire(row)
    return len(pending)


def prepare_embeddings(db: Session) -> int:
    """Called once at startup: load model and backfill missing/stale vectors."""
    settings = embedding_settings(db)
    if not settings.embeddings_enabled:
        return 0
    get_provider(db)  # Load even when the corpus is empty: fail before accepting requests.
    total = 0
    last_id = ''
    while True:
        batch = list(db.scalars(select(DocumentChunk).where(DocumentChunk.id > last_id)
                                .order_by(DocumentChunk.id).limit(settings.embedding_batch_size)))
        if not batch:
            break
        with transaction(db):
            total += stage_embeddings(db, batch)
        last_id = batch[-1].id
    return total


def semantic_search(db: Session, query: str, *, project_id: str | None, limit: int) -> list[dict]:
    """Small-corpus exhaustive cosine search, using the same scope as main FTS5."""
    settings = embedding_settings(db)
    provider = get_provider(db)
    statement = (select(DocumentChunk, Document.source_id, ChunkEmbedding)
                 .join(Document, Document.id == DocumentChunk.document_id)
                 .join(Source, Source.id == Document.source_id)
                 .outerjoin(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.id))
    if project_id is not None:
        statement = statement.where(Source.project_id == project_id)
    rows = db.execute(statement).all()
    if not rows:
        return []
    candidates = []
    for chunk, source_id, row in rows:
        if not _current(row, chunk, settings, provider.dimensions):
            raise APIError(503, 'embeddings_not_ready',
                           'Chunk embeddings are missing or stale; restart with embeddings enabled to prepare them')
        candidates.append((chunk, source_id, unit_vector(row.vector_json, provider.dimensions)))
    query_vector = unit_vector(provider.embed_query(query), provider.dimensions)
    scored = [(sum(a * b for a, b in zip(query_vector, vector)), chunk, source_id)
              for chunk, source_id, vector in candidates]
    scored.sort(key=lambda item: (-item[0], item[1].id))
    return [dict(id=chunk.id, document_id=chunk.document_id, source_id=source_id,
                 chunk_index=chunk.chunk_index, text=chunk.text)
            for _, chunk, source_id in scored[:limit]]
