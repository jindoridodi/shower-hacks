-- Versioned, normalized vectors for optional BGE semantic search.
-- The legacy document_chunks.embedding field remains untouched.
CREATE TABLE chunk_embeddings (
    chunk_id TEXT PRIMARY KEY REFERENCES document_chunks(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    model_revision TEXT NOT NULL,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0),
    text_hash TEXT NOT NULL CHECK (length(text_hash) = 64),
    vector_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Text edits invalidate embeddings. Other chunk updates do not.
CREATE TRIGGER chunk_embeddings_text_changed
AFTER UPDATE OF text ON document_chunks
WHEN new.text != old.text
BEGIN
    DELETE FROM chunk_embeddings WHERE chunk_id = new.id;
END;
