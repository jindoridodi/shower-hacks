
CREATE UNIQUE INDEX IF NOT EXISTS uq_report_claims_report_position
ON report_claims (report_id, position);

-- One queued or running job per source. Completed jobs stay in the table.
CREATE UNIQUE INDEX IF NOT EXISTS uq_crawl_jobs_one_active
ON crawl_jobs (source_id)
WHERE status IN ('queued', 'running');
