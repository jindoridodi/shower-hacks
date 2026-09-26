
CREATE UNIQUE INDEX IF NOT EXISTS uq_claim_sources_claim_source_excerpt
ON claim_sources (claim_id, source_id, excerpt);
