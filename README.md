# Borrowed Intimacy

Borrowed Intimacy is an experimental web-art project that turns publicly available web material into a source-linked portrait of a subject. It explores how quickly a system can produce the feeling of knowing someone from fragments of their online presence.

The system is deliberately constrained:

- It does not imitate a person's voice or writing style.
- It does not invent facts, memories, quotes, or events.
- It produces only source-backed statements and explicitly labeled inferences.
- Highly sensitive personal data is not passed into generation.
- It may draft source-grounded messages, posts, or emails for user review, but it never sends them automatically, impersonates the subject, or conceals that they were AI-generated.

## Project structure

```text
borrowed-intimacy/
├── apps/
│   ├── web/                         # Next.js interface
│   │   ├── app/
│   │   │   ├── page.tsx             # Landing page
│   │   │   ├── ingest/page.tsx      # Add public URLs
│   │   │   ├── corpus/[id]/page.tsx # Source corpus
│   │   │   ├── generate/page.tsx    # Factual output modes
│   │   │   └── reveal/page.tsx      # Evidence and uncertainty view
│   │   ├── components/
│   │   │   ├── SourceLedger.tsx
│   │   │   ├── EvidenceCard.tsx
│   │   │   ├── ConfidenceMeter.tsx
│   │   │   └── CorpusGraph.tsx
│   │   └── lib/api.ts
│   │
│   └── api/                         # FastAPI service
│       ├── main.py
│       ├── routes/
│       │   ├── projects.py
│       │   ├── sources.py
│       │   ├── crawls.py
│       │   └── reports.py
│       ├── services/
│       │   ├── firecrawl.py         # Public-page ingestion
│       │   ├── discovery.py         # Always-on public username discovery
│       │   ├── cleaner.py
│       │   ├── sensitivity.py       # Sensitive-data detection/filtering
│       │   ├── chunker.py
│       │   ├── embeddings.py
│       │   ├── retrieval.py
│       │   └── report_generator.py
│       └── schemas/
│           ├── project.py
│           ├── source.py
│           └── report.py
│
├── workers/
│   ├── crawl_worker.py
│   ├── embedding_worker.py
│   └── report_worker.py
│
├── packages/
│   ├── prompts/
│   │   ├── factual_profile.txt
│   │   ├── relationship_summary.txt
│   │   ├── uncertainty_report.txt
│   │   └── source_collision.txt
│   ├── safety/
│   │   ├── pii_patterns.py
│   │   ├── generation_policy.py
│   │   └── source_policy.py
│   └── types/
│       └── shared.ts
│
├── db/
│   ├── migrations/
│   └── schema.sql
├── data/
│   ├── raw/                         # Temporary crawl results
│   └── processed/                   # Filtered, normalized documents
├── scripts/
│   ├── import_urls.py
│   └── reset_demo.py
├── tests/
│   ├── test_firecrawl.py
│   ├── test_sensitivity.py
│   ├── test_retrieval.py
│   └── test_reports.py
├── .env.example
├── package.json
├── pyproject.toml
└── README.md
```

## Technology stack

### Application

- **Frontend:** Next.js, React, TypeScript, and Tailwind CSS
- **Backend:** Python, FastAPI, and Pydantic
- **API communication:** REST endpoints between the web client and FastAPI service

### Collection and processing

- **Web crawling:** Firecrawl API for public-page scraping and crawl jobs
- **Username discovery:** Sherlock, Maigret, WhatsMyName, and Namechk for suggesting and cross-checking publicly visible profile URLs
- **Browser fallback:** Playwright for public pages that require client-side rendering
- **Text extraction:** Firecrawl Markdown output, trafilatura, local normalization, and chunking
- **Historical pages:** Wayback Machine CDX API and Common Crawl as optional archival sources
- **Sensitive-data handling:** Presidio and custom detection rules

### Storage and retrieval

- **Primary database:** SQLite
- **Text search:** SQLite FTS5
- **Vector search:** `sqlite-vec` or a simple in-process embedding index
- **Optional search services:** Meilisearch or OpenSearch for larger installations
- **Object storage:** Local filesystem during development; S3-compatible storage in production
- **Background jobs:** Redis with Celery or BullMQ
- **Semantic search alternatives:** Qdrant or Chroma if SQLite vector search is insufficient
- **Graph visualization:** React Flow in the application, with Gephi or Maltego available for offline exploration

### Generation

- **Model interface:** OpenAI API or Ollama for local models
- **Embeddings:** Provider embeddings or a local sentence-transformer model
- **Retrieval pattern:** Evidence-constrained retrieval-augmented generation
- **Output formats:** Factual profiles, relationship summaries, uncertainty reports, source-collision views, and reviewed communication drafts

### Optional media and metadata tools

- **Metadata inspection:** ExifTool for public image and document metadata
- **Public media archiving:** yt-dlp only for explicitly public media and permitted use
- **Public place context:** OpenStreetMap/Nominatim for interpreting places already named in public sources; never for locating a person

### Infrastructure

- **Frontend hosting:** Vercel or equivalent Node-compatible hosting
- **API and workers:** Render, Fly.io, or Docker-compatible hosting
- **Local orchestration:** Docker Compose
- **Testing:** Pytest for the API and workers; Vitest or Jest for the frontend
- **Observability:** Structured JSON logs and crawl/job status records

## Output modes

The generator supports evidence-based outputs only:

1. **Factual profile** — statements directly supported by collected sources.
2. **Relationship summary** — recurring themes, interests, and public self-description, with citations.
3. **Uncertainty report** — what the corpus cannot establish and where sources conflict.
4. **Source collision** — a visual comparison of how different pages produce competing impressions.
5. **Communication draft** — a source-linked draft addressed to a recipient, clearly labeled as AI-generated and requiring manual review before sending.

Every generated statement should link to one or more source records. If no adequate source exists, the system should say that it does not know.

## Data flow

```text
Public URL list
    ↓
Firecrawl
    ↓
Raw document + URL + timestamp + content hash
    ↓
Cleaner and sensitive-data filter
    ↓
Chunks and embeddings
    ↓
SQLite / FTS5 / optional sqlite-vec
    ↓
Evidence-constrained retrieval
    ↓
Factual report
    ↓
Source ledger and uncertainty view
```

The discovery service runs Sherlock, Maigret, and WhatsMyName for username queries to suggest publicly visible profile URLs. Suggested URLs must be reviewed and added to the crawl allowlist; manually supplied public URLs use the direct-input path.

## Suggested database tables

```text
projects
sources
documents
document_chunks
entities
reports
report_claims
claim_sources
```

Important fields include:

- `sources.url`
- `sources.canonical_url`
- `sources.scraped_at`
- `sources.content_hash`
- `documents.sensitivity_status`
- `report_claims.claim_text`
- `claim_sources.source_id`
- `claim_sources.excerpt`

## Local development

### Requirements

- Node.js 20+
- Python 3.11+
- SQLite 3; FTS5 is recommended and `sqlite-vec` is optional
- Redis, if asynchronous workers are enabled
- A Firecrawl API key

### Environment

Copy `.env.example` to `.env` and configure:

```text
FIRECRAWL_API_KEY=
APIFY_API_TOKEN=
DATABASE_URL=sqlite:///./data/borrowed_intimacy.db
REDIS_URL=redis://localhost:6379/0
LLM_API_KEY=
OSINT_USE_FIXTURES=false # Fixture data is for offline tests/demos only.
SHERLOCK_SITE_TIMEOUT_SECONDS=10
SHERLOCK_PROCESS_TIMEOUT_SECONDS=45
MAIGRET_SITE_TIMEOUT_SECONDS=10
MAIGRET_PROCESS_TIMEOUT_SECONDS=60
MAIGRET_MAX_SITES=500
WHATS_MY_NAME_DATA_URL=https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json
WHATS_MY_NAME_CACHE_TTL_SECONDS=86400
WHATS_MY_NAME_SITE_TIMEOUT_SECONDS=8
WHATS_MY_NAME_MAX_CONCURRENCY=20
```

## How to run the OSINT test service

The OSINT service includes a small browser interface and a JSON API for testing candidate URL discovery. It does not crawl discovered URLs. The UI can create local projects and save any direct public HTTP(S) URL against a username; those saved links are kept in SQLite and merge into later searches for the same project and username.

### 1. Create the local environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### 2. Run in fixture mode

Fixture mode uses the predictable demo data in `data/fixtures/candidates.json`. It is the best choice for frontend work and offline demos.

```bash
OSINT_USE_FIXTURES=true python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) to use the browser test UI, or test the API directly:

```bash
curl -X POST http://127.0.0.1:8000/api/discovery \
  -H 'Content-Type: application/json' \
  -d '{"query":"demo-user"}'
```

To use persistent saved links, create a project, then add a URL for a username:

```bash
PROJECT_ID=$(curl -sS -X POST http://127.0.0.1:8000/api/projects \
  -H 'Content-Type: application/json' \
  -d '{"name":"demo"}' | python -c 'import json,sys; print(json.load(sys.stdin)["projectId"])')

curl -X POST "http://127.0.0.1:8000/api/projects/$PROJECT_ID/sources" \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo-user","url":"https://example.com/profile"}'

curl -X POST http://127.0.0.1:8000/api/discovery \
  -H 'Content-Type: application/json' \
  -d "{\"query\":\"demo-user\",\"projectId\":\"$PROJECT_ID\"}"
```

`data/borrowed_intimacy.db` is local runtime state and is intentionally ignored by Git.

### 3. Run live public-profile discovery

Stop the fixture server with `Ctrl+C`, then run:

```bash
OSINT_USE_FIXTURES=false python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Every username query runs Sherlock, Maigret, and WhatsMyName. A provider failure is reported as a warning while successful providers still return candidate URLs.

Test a public username:

```bash
curl -X POST http://127.0.0.1:8000/api/discovery \
  -H 'Content-Type: application/json' \
  -d '{"query":"openai","limit":5}'
```

Live results are candidate username matches, not verified identity matches.

### 4. Run automated tests

```bash
python -m pytest
```

### Development order

1. Accept an explicit list of public URLs.
2. Crawl and store pages through Firecrawl.
3. Normalize text and detect sensitive fields.
4. Index safe document chunks.
5. Retrieve supporting excerpts for each report claim.
6. Render the report with citations and uncertainty labels.
7. If a communication draft is requested, show its sources and require an explicit human review before export.

## Crawl policy

The prototype should crawl only publicly accessible pages, avoid authentication and access-control bypasses, respect applicable site terms and robots directives, rate-limit requests, and keep the crawl scope explicit. It should not collect passwords, private messages, financial records, health information, precise private location data, or private contact details for generation.

Communication drafts must not claim to be written by the target, use the target's private identity, or be sent automatically. The interface should visibly label them as AI-generated and preserve their source citations.

## Backend slice

The FastAPI service in `apps/api` covers projects, manually supplied public URLs, crawl jobs, documents, searchable chunks, and claim-to-source evidence. Pages are stored when a caller supplies text or a `ScrapedPage`. The Firecrawl client itself is a plug-in point in `apps/api/services/firecrawl.py`.

`POST /instagram/profiles` accepts one public Instagram username and returns a normalized profile plus up to 10 recent caption-bearing posts from Apify's `apify/instagram-profile-scraper`. It returns image URLs but does not download or analyze images.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python scripts/migrate.py
```

### Migrations

`python scripts/migrate.py` applies every new file in `db/migrations` and records it in `schema_migrations`. Run it again after it succeeds and it leaves the database unchanged. `db/schema.sql` is the full schema snapshot: the initial migration plus later files, in order.

Starting the API applies pending migrations too:

```bash
uvicorn apps.api.main:app --reload
```

SQLite foreign keys are enabled on each connection. FTS5 indexes `document_chunks`.

### Seed and reset

```bash
python scripts/seed.py
python scripts/reset_db.py
```

`scripts/seed.py` creates a project named `Demo` and the public source `https://example.com/` when they are absent. Running it twice keeps a single project and source.

`scripts/reset_db.py` deletes only `data/borrowed_intimacy.db` inside this repository, plus the SQLite `-wal` and `-shm` files beside it, then recreates the empty schema. Any other `DATABASE_URL` is refused.

### Tests

```bash
pytest
```

### API

Error responses look like:

```json
{"detail": {"code": "duplicate_canonical_url", "message": "A source with canonical URL https://example.com/ already exists in this project"}}
```

Request validation uses the code `validation_error`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Database connectivity check |
| `POST` | `/projects` | Create a project |
| `GET` | `/projects/{project_id}` | Fetch a project |
| `POST` | `/sources` | Add a public URL to a project |
| `GET` | `/sources?project_id=` | List sources for a project |
| `GET` | `/sources/{source_id}` | Fetch a source |
| `POST` | `/sources/{source_id}/queue` | Queue a crawl for a source |
| `POST` | `/crawls` | Create a crawl job (`{"source_id": "..."}`) |
| `GET` | `/crawls?source_id=` | List crawl jobs for a source |
| `GET` | `/crawls/{crawl_id}` | Fetch a crawl job |
| `PATCH` | `/crawls/{crawl_id}` | Move a job through `running`, `succeeded`, or `failed` |
| `POST` | `/documents` | Store document text; the same content hash for one source returns the existing row |
| `GET` | `/documents/{document_id}` | Fetch a document |
| `POST` | `/documents/{document_id}/chunks` | Insert chunks (`{"chunks": [{"chunk_index": 0, "text": "..."}]}`) |
| `GET` | `/documents/{document_id}/chunks` | List chunks |
| `GET` | `/search/chunks?q=` | Full-text search over chunk text |
| `POST` | `/reports` | Create a report shell for evidence |
| `GET` | `/reports/{report_id}` | Fetch a report with claims and excerpts |
| `POST` | `/reports/{report_id}/claims` | Add a claim and optional source excerpts |
| `POST` | `/report-claims/{claim_id}/sources` | Link another source excerpt to a claim |
| `POST` | `/api/projects/{project_id}/crawls` | Queue a crawl when the source belongs to that corpus project |
| `GET` | `/api/crawls/{crawl_id}` | Fetch the same crawl job as `GET /crawls/{crawl_id}` |
| `PATCH` | `/api/crawls/{crawl_id}` | Same status update as `PATCH /crawls/{crawl_id}` |
| `GET` | `/api/projects/{project_id}/corpus` | List corpus sources, documents, and chunks |
| `POST` | `/api/projects/{project_id}/reports/persisted` | Store a generated report and its excerpts |
| `GET` | `/api/reports/{report_id}` | Fetch the same stored report as `GET /reports/{report_id}` |

Source creation body:

```json
{"project_id": "PROJECT_ID", "url": "https://example.com/about"}
```

Canonical URLs are unique inside a project. `https://Example.com/about/` and `https://example.com/about` are the same source. The stored `url` keeps the submitted string; `canonical_url` is the normalized form.

Crawl status values are `queued`, `running`, `succeeded`, and `failed`. A failed update requires `error_message`. `sources.status` follows the latest job. A new source starts as `pending`. `scraped_at` is set when a job succeeds.

Document body:

```json
{
  "source_id": "SOURCE_ID",
  "title": "About",
  "cleaned_text": "Public biography text",
  "raw_text": "<p>Public biography text</p>",
  "sensitivity_status": "unreviewed"
}
```

`content_hash` is the SHA-256 hex digest of `cleaned_text` when that field is present, otherwise of `raw_text`. Sending a hash that does not match the text returns `content_hash_mismatch`. Posting the same hash again for the same source returns HTTP 200 with `deduplicated: true`.

Claim body:

```json
{
  "claim_text": "The page describes a public biography.",
  "sources": [
    {"source_id": "SOURCE_ID", "excerpt": "Public biography text"}
  ]
}
```

Every claim-source row stores an excerpt. The source must belong to the report's project.

### Database

| Table | Role |
| --- | --- |
| `projects` | A portrait workspace |
| `sources` | Public URL, canonical URL, status, content hash, `scraped_at` |
| `crawl_jobs` | One crawl attempt: status, error message, start and completion times |
| `documents` | Raw text, cleaned text, content hash, `sensitivity_status` |
| `document_chunks` | Ordered chunk text for a document |
| `document_chunks_fts` | FTS5 index kept in sync by triggers |
| `reports` | A report shell for later generation |
| `report_claims` | `claim_text` attached to a report |
| `claim_sources` | `source_id` plus `excerpt` for a claim |

`sensitivity_status` is one of `unreviewed`, `clear`, `sensitive`, or `redacted`. New documents from the scraper seam are stored as `unreviewed`.

`claim_sources.source_id` uses `ON DELETE RESTRICT`, so a cited source stays in place while a claim quotes it.

### Firecrawl follow-up

`get_public_page_scraper()` returns `FirecrawlPublicPageScraper` when `FIRECRAWL_API_KEY` is set, and a stub that raises `FirecrawlNotConfiguredError` otherwise. The configured client only scrapes URLs listed in `CRAWL_ALLOWED_URLS` whose hosts are listed in `CRAWL_TERMS_ACCEPTED_HOSTS`. It checks robots.txt, rate-limits requests, and retries transient Firecrawl errors. `run_queued_crawl` loads a queued job, scrapes `sources.url`, and calls `ingest_scraped_page`. A scraper exception marks the job `failed`. `ingest_scraped_page` still accepts a page only when its URL canonicalizes to the source URL, and the stored document remains `unreviewed`.

The corpus contract is documented in `docs/04-integration-contract.md`. Crawl jobs use `queued`, `running`, `succeeded`, and `failed`. `complete` and `partial` are not crawl statuses. Corpus errors use `{"detail": {"code", "message"}}`. `POST /api/projects` remains the OSINT project route and writes a different database. `POST /api/projects/{project_id}/reports/persisted` stores a generated report; `POST /api/projects/{project_id}/reports` only generates one.

Stored pages use `documents.raw_text`, `documents.cleaned_text`, and `documents.raw_path` for the markdown file written at ingest. Chunks use `document_chunks.text` and `document_chunks.fts_text`. Search reads `document_chunks_fts`. `document_chunks.embedding` is stored as null until an embedding worker exists.

## License

### People search handoff

The current Firecrawl search implementation is intentionally deferred to the
other branch. The latest candidate URL fixture is
[`documents/people-search-urls.json`](documents/people-search-urls.json). It
contains the URLs to feed into the merged search/scrape workflow later.

The shared output contract remains documented in
[`docs/tests/people-search-schema.md`](docs/tests/people-search-schema.md).

Add the project’s license before public release.
