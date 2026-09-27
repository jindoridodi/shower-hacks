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
