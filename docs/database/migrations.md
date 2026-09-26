# Migrations

For the hackathon, use one idempotent schema initializer. If schema changes are needed, record them here and increment a local schema version.

- [ ] `001_initial.sql` — projects, sources, documents, claims
- [ ] `002_search.sql` — FTS5 index
- [ ] `003_fixture_metadata.sql` — optional demo metadata

Never delete the only working database during the demo. Use a separate reset command.
