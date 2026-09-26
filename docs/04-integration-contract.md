# Integration Contract

## API endpoints

This process serves three documented surfaces. Paths are not interchangeable: OSINT projects live in a separate SQLite file from the corpus ledger.

### Corpus ledger

Database: `data/borrowed_intimacy.db`, created by `db/migrations`.

```text
POST /projects
GET  /projects/{project_id}
POST /sources
GET  /sources?project_id=
GET  /sources/{source_id}
POST /sources/{source_id}/queue
POST /crawls
GET  /crawls?source_id=
GET  /crawls/{crawl_id}
PATCH /crawls/{crawl_id}
POST /documents
GET  /documents/{document_id}
POST /documents/{document_id}/chunks
GET  /documents/{document_id}/chunks
GET  /search/chunks?q=
POST /reports
GET  /reports/{report_id}
POST /reports/{report_id}/claims
POST /report-claims/{claim_id}/sources
POST /api/projects/{project_id}/crawls
GET  /api/crawls/{crawl_id}
PATCH /api/crawls/{crawl_id}
GET  /api/projects/{project_id}/corpus
POST /api/projects/{project_id}/reports/persisted
GET  /api/reports/{report_id}
GET  /health
```

The `/api/projects/{project_id}/crawls`, `/api/crawls/{crawl_id}`, `/api/projects/{project_id}/corpus`, and `/api/reports/{report_id}` routes are aliases over the same corpus records as the unprefixed routes. `POST /api/projects/{project_id}/reports/persisted` writes a generated report into `reports`, `report_claims`, and `claim_sources`.

`POST /api/projects` and `POST /api/projects/{project_id}/sources` are not corpus aliases. Those paths belong to the OSINT surface below.

### OSINT manual sources

Database: `OSINT_DATABASE_URL`, default `sqlite:///./data/osint_sources.db`.

```text
POST /api/projects
GET  /api/projects
POST /api/discovery
POST /api/graph/export?format=csv|gexf
POST /api/enrichment/spiderfoot
GET  /api/enrichment/spiderfoot/{job_id}
POST /api/projects/{project_id}/sources
GET  /api/projects/{project_id}/sources?username={username}
DELETE /api/projects/{project_id}/sources/{source_id}
GET  /api/health
```

### Generation

`POST /api/projects/{project_id}/reports` and `POST /api/projects/{project_id}/drafts` return generated JSON. They do not write the corpus database. Pass `useFixtures: true` to skip the model provider. To store a generated report, call `POST /api/projects/{project_id}/reports/persisted` with the report object and the excerpts that were used.

## Crawl job

A crawl job belongs to one corpus source. Status values are `queued`, `running`, `succeeded`, and `failed`. `complete` and `partial` are not crawl statuses. `partial` on `POST /api/discovery` is a separate boolean for provider failures.

```json
{
  "id": "crawl_001",
  "source_id": "source_001",
  "status": "queued",
  "error_message": null,
  "started_at": null,
  "completed_at": null,
  "created_at": "2026-09-26T18:00:00.000000+00:00",
  "updated_at": "2026-09-26T18:00:00.000000+00:00"
}
```

`POST /api/projects/{project_id}/crawls` accepts `{ "source_id": "..." }`. The source must belong to that corpus project.

## Error response

Corpus errors use one envelope:

```json
{
  "detail": {
    "code": "crawl_already_active",
    "message": "This source already has a queued or running crawl"
  }
}
```

Request validation uses the code `validation_error`. OSINT routes that raise FastAPI `HTTPException` put a string in `detail` instead of this object.

## Stored report fields

Corpus claims are stored as `claim_text` plus `claim_sources.excerpt`. The persisted route accepts the generation field names `claimType` and `sourceIds`, and stores an excerpt for every cited source. `unknown` claims and `unknowns` are stored as claims with no `claim_sources` rows. Contradictions and `generatedAt` are not stored. There is no `partial` citation state.

Sensitivity values `sensitive`, `restricted`, and `redacted` are rejected. A citation is also rejected when the excerpt appears in a `sensitive` or `redacted` document, or when the source's current document has one of those statuses. `safe`, `clear`, and `unreviewed` may be cited.

## Schema names

`documents.raw_text` stores optional raw HTML. `documents.cleaned_text` stores cleaned markdown. `documents.raw_path` is the repo-relative file written during ingest. `document_chunks.text` is the chunk body, and `document_chunks.fts_text` stores the same text for the shared chunk contract. Search uses `document_chunks_fts` through `GET /search/chunks`. `document_chunks.embedding` exists and stays null until a later embedding milestone.

`POST /instagram/profiles` reads one public Instagram username through Apify. It is not part of the corpus crawl flow.

## Discovery response

`POST /api/discovery` returns candidate public URLs only. It never crawls or generates reports. The endpoint infers a direct URL from an `http://` or `https://` query; every other query is handled as a username. `queryType` remains accepted for backward compatibility. When the optional `projectId` is provided for a username query, it also merges locally saved user-supplied sources for that exact project and normalized username.

```json
{
  "query": "demo-user",
  "candidates": [],
  "providersUsed": ["sherlock", "maigret", "whatsmyname"],
  "providerEvidence": {},
  "savedSources": [],
  "partial": false,
  "warnings": []
}
```

Username discovery always runs Sherlock, Maigret, and WhatsMyName. Empty candidates are a successful result; provider failures use `partial` and `warnings`. Saved sources carry `user_supplied` evidence and high confidence because they were deliberately attached, not because they prove identity.

`POST /api/projects/{project_id}/sources` accepts `{ "username": "demo-user", "url": "https://example.com/profile" }`. URLs must be direct public HTTP(S) URLs; saving does not fetch, crawl, or enrich them.

`POST /api/graph/export` accepts the discovery `query`, `candidates`, and `providerEvidence`, then returns a CSV ZIP or GEXF download. SpiderFoot enrichment only accepts an explicitly selected public URL, username, or domain and never starts a crawl.
