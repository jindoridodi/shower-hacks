# Search and Retrieval

## MVP

Use SQLite FTS5 to retrieve excerpts by keyword and source ID.

## Optional semantic search

Add `sqlite-vec` only after the keyword path works. The report generator must receive source IDs and excerpts regardless of search method.

## Checklist

- [ ] Return top-k excerpts.
- [ ] Preserve source IDs.
- [ ] Deduplicate near-identical excerpts.
- [ ] Prefer attributable text.
- [ ] Return an empty result rather than inventing support.
