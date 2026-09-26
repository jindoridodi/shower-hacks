# Architecture

```text
Next.js frontend
        |
        v
FastAPI API
  |       |        |
  v       v        v
Discovery Firecrawl SQLite
                    |
                    v
              FTS5 / sqlite-vec
                    |
                    v
          Evidence-constrained retrieval
                    |
                    v
           Reports and reviewed drafts
```

## Runtime boundaries

- The frontend owns interaction and presentation.
- The API owns validation and orchestration.
- Firecrawl owns public-page retrieval.
- SQLite owns project, source, document, and claim records.
- The generator receives retrieved safe excerpts, not unrestricted raw data.

## Request lifecycle

1. Create a project.
2. Add explicit public URLs.
3. Start a crawl job.
4. Store metadata and normalized content.
5. Detect sensitive fields.
6. Index safe chunks.
7. Retrieve supporting excerpts.
8. Generate claims with citations.
9. Render the report and source ledger.
