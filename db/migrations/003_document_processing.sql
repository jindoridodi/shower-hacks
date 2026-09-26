-- Store only filtered metadata and category labels, never rejected values.
ALTER TABLE documents ADD COLUMN processing_metadata TEXT NOT NULL DEFAULT '{}';
ALTER TABLE documents ADD COLUMN sensitivity_findings TEXT NOT NULL DEFAULT '[]';
ALTER TABLE documents ADD COLUMN metadata_findings TEXT NOT NULL DEFAULT '[]';

-- This is a standalone FTS5 table, so use ordinary DELETE rather than the
-- special 'delete' command intended for external-content/contentless tables.
DROP TRIGGER IF EXISTS document_chunks_ad;
CREATE TRIGGER document_chunks_ad
AFTER DELETE ON document_chunks
BEGIN
    DELETE FROM document_chunks_fts WHERE chunk_id = old.id;
END;

DROP TRIGGER IF EXISTS document_chunks_au;
CREATE TRIGGER document_chunks_au
AFTER UPDATE ON document_chunks
BEGIN
    DELETE FROM document_chunks_fts WHERE chunk_id = old.id;
    INSERT INTO document_chunks_fts (chunk_id, text)
    VALUES (new.id, new.text);
END;
