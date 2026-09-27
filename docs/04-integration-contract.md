# Integration Contract

## API endpoints

This process serves three documented surfaces. The corpus ledger is the source
of truth for projects, sources, crawls, and reports. The legacy OSINT
saved-source store is separate and does not grant crawl permission.

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

The `/api/projects/{project_id}/crawls`, `/api/crawls/{crawl_id}`,
`/api/projects/{project_id}/corpus`, and `/api/reports/{report_id}` routes are
aliases over the same corpus records as the unprefixed routes.
`POST /api/projects/{project_id}/reports/persisted` writes a generated report
into `reports`, `report_claims`, and `claim_sources`.

### OSINT manual sources

Database: `OSINT_DATABASE_URL`, default `sqlite:///./data/osint_sources.db`.
These endpoints are a discovery-only compatibility surface; they cannot create
or queue corpus sources.

```text
POST /api/osint/projects
GET  /api/osint/projects
POST /instagram/profiles
POST /api/discovery
POST /api/approvals
GET  /api/approvals?projectId={project_id}
POST /api/graph/export?format=csv|gexf
POST /api/enrichment/spiderfoot
GET  /api/enrichment/spiderfoot/{job_id}
POST /api/osint/projects/{project_id}/sources
GET  /api/osint/projects/{project_id}/sources?username={username}
DELETE /api/osint/projects/{project_id}/sources/{source_id}
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

The unprefixed ledger endpoints (`/projects`, `/sources`, and `/crawls`) remain
available for compatibility. The OSINT prototype's separate saved-source store
is available only at `/api/osint/projects/...`; it is not a crawl allowlist and
cannot queue a crawl.

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

`POST /api/projects/{project_id}/sources` accepts
`{ "url": "https://example.com/profile" }`. URLs must be direct public HTTP(S)
targets: credentialed, loopback, and private IP targets are rejected. Creating a
source does not fetch, crawl, or enrich it. It starts with
`approval_status: "pending"` and `is_allowlisted: false`.

`PATCH /api/projects/{project_id}/sources/{source_id}/approval` accepts
`{ "approval_status": "approved" | "rejected" }`. Only an approved,
allowlisted source may be queued. `POST /api/approvals` is the discovery
candidate path: it stores candidate provenance and creates an already-approved,
allowlisted source, but never queues it.

Run one worker iteration with:

```bash
python -m workers.crawl_worker --once
```

The worker only claims approved, allowlisted queued jobs. It records a terminal
failure when Firecrawl is unavailable or retrieval fails, without logging
credentials or crawled content.

`POST /api/graph/export` accepts the discovery `query`, `candidates`, and `providerEvidence`, then returns a CSV ZIP or GEXF download.

## Instagram profile response

`POST /instagram/profiles` accepts one public Instagram username:

```json
{ "username": "example.user" }
```

It returns normalized profile fields: `username`, `full_name`, `biography`, `profile_url`, `profile_picture_url`, `external_url`, `category`, profile counts, `is_verified`, `is_private`, and up to ten caption-bearing `recent_posts`. URLs remain strings; the endpoint does not download media, create sources, or queue crawls.

For private profiles, only the username, canonical profile URL, private/verified flags, and available counts are returned. Name, biography, image, external URL, category, and posts are redacted to `null` or `[]`.

Errors use the normal API `detail` envelope with `code`, `message`, and `retryable`:

| Status | Code | Retryable |
| --- | --- | --- |
| 503 | `apify_not_configured` | no |
| 503 | `apify_auth_failed` | no |
| 404 | `instagram_profile_not_found` | no |
| 503 | `instagram_provider_unavailable` | yes |
| 502 | `instagram_invalid_response` | no |
| 502 | `instagram_provider_rejected` | no |

Set `INSTAGRAM_USE_FIXTURES=true` to use `demo.public`, `demo.private`, `demo.missing`, and `demo.unavailable` from `data/fixtures/instagram-profiles.json`. Fixture mode is explicit and never replaces a failed live lookup.
