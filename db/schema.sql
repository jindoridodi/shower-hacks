-- Borrowed Intimacy source, document, and evidence schema.
-- The migration runner applies db/migrations and records versions in schema_migrations.
-- Statements use IF NOT EXISTS so a repeated apply does not destroy data.
--
-- SQLite does not persist PRAGMA foreign_keys. The application enables it on every connection.
--
-- crawl_jobs is the crawl-attempt log (status, error, timestamps). sources.status mirrors
-- the latest attempt so source lists stay simple.
--
-- A document belongs to one source. content_hash is unique per source, so crawling the
-- same page again does not store a second copy. The same hash may exist on another source.
--
-- claim_sources.source_id uses ON DELETE RESTRICT so a cited source cannot be removed
-- while a claim still quotes it.
--
-- document_chunks_fts is a standalone FTS5 index kept in sync by triggers. Chunk text is
-- copied into the index so search does not depend on SQLite rowids, which VACUUM can change.

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'queued', 'running', 'succeeded', 'failed')
    ),
    content_hash TEXT CHECK (
        content_hash IS NULL OR length(content_hash) = 64
    ),
    scraped_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (project_id, canonical_url)
);

CREATE TABLE IF NOT EXISTS crawl_jobs (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed')
    ),
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_crawl_jobs_source_id ON crawl_jobs (source_id);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
    title TEXT,
    content_type TEXT,
    raw_text TEXT,
    cleaned_text TEXT,
    sensitivity_status TEXT NOT NULL DEFAULT 'unreviewed' CHECK (
        sensitivity_status IN ('unreviewed', 'clear', 'sensitive', 'redacted')
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (source_id, content_hash),
    CHECK (
        (cleaned_text IS NOT NULL AND length(cleaned_text) > 0)
        OR (raw_text IS NOT NULL AND length(raw_text) > 0)
    )
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    text TEXT NOT NULL CHECK (length(trim(text)) > 0),
    created_at TEXT NOT NULL,
    UNIQUE (document_id, chunk_index)
);

CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(
    chunk_id UNINDEXED,
    text
);

CREATE TRIGGER IF NOT EXISTS document_chunks_ai
AFTER INSERT ON document_chunks
BEGIN
    INSERT INTO document_chunks_fts (chunk_id, text)
    VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS document_chunks_ad
AFTER DELETE ON document_chunks
BEGIN
    INSERT INTO document_chunks_fts (document_chunks_fts, chunk_id, text)
    VALUES ('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS document_chunks_au
AFTER UPDATE ON document_chunks
BEGIN
    INSERT INTO document_chunks_fts (document_chunks_fts, chunk_id, text)
    VALUES ('delete', old.id, old.text);
    INSERT INTO document_chunks_fts (chunk_id, text)
    VALUES (new.id, new.text);
END;

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_project_id ON reports (project_id);

CREATE TABLE IF NOT EXISTS report_claims (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports (id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL CHECK (length(trim(claim_text)) > 0),
    position INTEGER NOT NULL DEFAULT 0 CHECK (position >= 0),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_report_claims_report_id ON report_claims (report_id);

CREATE TABLE IF NOT EXISTS claim_sources (
    id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES report_claims (id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources (id) ON DELETE RESTRICT,
    excerpt TEXT NOT NULL CHECK (length(trim(excerpt)) > 0),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claim_sources_claim_id ON claim_sources (claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_sources_source_id ON claim_sources (source_id);
-- Shared Source/Document/DocumentChunk contract additions.
ALTER TABLE documents ADD COLUMN raw_path TEXT;
ALTER TABLE document_chunks ADD COLUMN embedding TEXT;
ALTER TABLE document_chunks ADD COLUMN fts_text TEXT NOT NULL DEFAULT '';

UPDATE document_chunks SET fts_text = text WHERE fts_text = '';

CREATE UNIQUE INDEX IF NOT EXISTS uq_report_claims_report_position
ON report_claims (report_id, position);

-- One queued or running job per source. Completed jobs stay in the table.
CREATE UNIQUE INDEX IF NOT EXISTS uq_crawl_jobs_one_active
ON crawl_jobs (source_id)
WHERE status IN ('queued', 'running');

CREATE UNIQUE INDEX IF NOT EXISTS uq_claim_sources_claim_source_excerpt
ON claim_sources (claim_id, source_id, excerpt);
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
CREATE TABLE source_approvals (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL UNIQUE REFERENCES sources (id) ON DELETE CASCADE,
    target_username TEXT NOT NULL,
    platform TEXT NOT NULL,
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    match_reason TEXT NOT NULL,
    provider_evidence TEXT NOT NULL,
    approved_at TEXT NOT NULL
);

CREATE INDEX idx_source_approvals_target_username
ON source_approvals (target_username);
