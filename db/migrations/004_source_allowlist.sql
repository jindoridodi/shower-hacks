-- A source can exist before it is approved. Queueing and worker execution use
-- these fields as the project-local crawl allowlist boundary.
ALTER TABLE sources ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (approval_status IN ('pending', 'approved', 'rejected'));
ALTER TABLE sources ADD COLUMN is_allowlisted INTEGER NOT NULL DEFAULT 0
    CHECK (is_allowlisted IN (0, 1));
ALTER TABLE sources ADD COLUMN approved_at TEXT;
ALTER TABLE sources ADD COLUMN approval_origin TEXT;

-- Candidate approvals predate this migration. Preserve their already explicit
-- approval semantics when upgrading an existing database.
UPDATE sources
SET approval_status = 'approved',
    is_allowlisted = 1,
    approved_at = (
        SELECT approved_at FROM source_approvals
        WHERE source_approvals.source_id = sources.id
    ),
    approval_origin = 'discovery'
WHERE id IN (SELECT source_id FROM source_approvals);

CREATE INDEX idx_sources_project_allowlisted
ON sources (project_id, is_allowlisted);
