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
├── infra/spiderfoot/docker-compose.yml
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
- **OSINT correlation:** SpiderFoot with breach, phone, dark-web, and precise-location modules disabled

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
SPIDERFOOT_BASE_URL=http://127.0.0.1:5001
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

### 4. Run selected-source SpiderFoot enrichment

Start the local SpiderFoot v4.0 sidecar. The repository provides an Apple-Silicon-compatible wrapper because SpiderFoot's upstream v4.0 Alpine/Python 3.8 image cannot build its pinned PyYAML dependency on ARM.

```bash
docker compose -f infra/spiderfoot/docker-compose.yml up --build -d
```

After discovery, send only a source you explicitly selected:

```bash
curl -X POST http://127.0.0.1:8000/api/enrichment/spiderfoot \
  -H 'Content-Type: application/json' \
  -d '{"target":"demo-user","targetType":"username","modules":["account_discovery"]}'
```

SpiderFoot findings are not candidates automatically and never trigger Firecrawl.

### 5. Run automated tests

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

## License

Add the project’s license before public release.
