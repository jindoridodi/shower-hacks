-- Shared Source/Document/DocumentChunk contract additions.
ALTER TABLE documents ADD COLUMN raw_path TEXT;
ALTER TABLE document_chunks ADD COLUMN embedding TEXT;
ALTER TABLE document_chunks ADD COLUMN fts_text TEXT NOT NULL DEFAULT '';

UPDATE document_chunks SET fts_text = text WHERE fts_text = '';
