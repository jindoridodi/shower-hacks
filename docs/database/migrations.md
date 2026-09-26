# Migrations

`python scripts/migrate.py` applies each file in `db/migrations` once and records the version in `schema_migrations`. Running it again is a no-op. `db/schema.sql` is the concatenation of those files.

- `001_initial.sql` — projects, sources, crawl jobs, documents, chunks, FTS5, reports, claims
- `002_raw_document_contract.sql` — `documents.raw_path`, `document_chunks.embedding`, `document_chunks.fts_text`
- `002_uniqueness.sql` — one active crawl per source, unique claim positions
- `003_claim_source_excerpt.sql` — one excerpt row per claim, source, and excerpt text
- `003_source_approvals.sql` — approval provenance for a canonical source

Do not edit a file after it has been applied. Add a new file. `scripts/reset_db.py` deletes only the local corpus database.
