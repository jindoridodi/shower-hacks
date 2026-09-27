# freakypeeky

freakypeeky is a web-art prototype for exploring how public online fragments can be assembled into a portrait-like experience. It combines public username discovery, user-selected public links, Instagram profile lookup, source/corpus workflows, and source-grounded AI drafts.

The project treats discovery results as suggestions, not identity proof. It does not log into accounts, bypass access controls, download Instagram media, or automatically crawl a discovered link.

## What works today

- Public username discovery through Sherlock, Maigret, and WhatsMyName.
- Direct public URL validation and normalization.
- Project-scoped manual public links stored in SQLite.
- Candidate evidence, confidence scoring, deduplication, and Gephi graph export.
- Instagram public-profile lookup through Apify, with deterministic fixtures for demos.
- Private Instagram profiles return only limited metadata; biography, image, external URL, category, and posts are omitted.
- Source, crawl, document, chunk, report, and approval API routes backed by SQLite.
- An OpenAI-compatible LLM adapter for evidence-grounded reports and review-only communication drafts.
- A branded Next.js prototype frontend for the project experience.

## Current limitations

- The Next.js UI at port `3000` still uses mock search and personalization data; it does not call the live API yet. Use Swagger at port `8000` to exercise the backend directly.
- Discovery candidates are possible username matches, not verified accounts belonging to one person.
- Live username providers and Apify can be rate-limited or blocked by their upstream services.
- Crawl jobs and report generation require configured sources, approved URLs, and their respective provider keys.
- The OSINT saved-link store and corpus/source workflow are currently separate SQLite-backed slices that still need end-to-end consolidation.
- SpiderFoot is not part of this project.

## Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: Python 3.11, FastAPI, Pydantic, SQLAlchemy
- Database: SQLite with FTS5
- Discovery: Sherlock, Maigret, WhatsMyName
- Instagram: Apify `apify/instagram-profile-scraper`
- Generation: OpenAI-compatible chat-completions API
- Graph export: NetworkX to CSV ZIP or GEXF
- Tests: pytest

## Repository layout

```text
apps/
  api/                 FastAPI app, routes, services, and schemas
  web/                 Next.js visual prototype
data/fixtures/         Deterministic discovery, Instagram, report, and draft data
db/migrations/         SQLite migrations
packages/prompts/      Structured report and draft prompts
scripts/               Database migration, seed, reset, and utility commands
tests/                 Backend, generation, ingestion, and persistence tests
docs/                  API contracts, work plans, setup notes, and team handoffs
```

## Local setup

Requirements:

- Python 3.11+
- Node.js 20+
- An optional Apify token for live Instagram lookups
- An optional OpenAI-compatible API key and model for live generation

Create the Python environment and install the backend:

```bash
cd /Users/chuu/Desktop/shower-hacks
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,osint]'
cp .env.example .env
python scripts/migrate.py
```

Configure only the providers you intend to use in `.env`:

```env
DATABASE_URL=sqlite:///./data/borrowed_intimacy.db

# Live Instagram lookup
APIFY_API_TOKEN=
APIFY_INSTAGRAM_ACTOR=apify~instagram-profile-scraper
INSTAGRAM_USE_FIXTURES=false

# Live LLM generation
LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=

# Optional crawling
FIRECRAWL_API_KEY=
CRAWL_ALLOWED_URLS=
CRAWL_TERMS_ACCEPTED_HOSTS=
```

Keep secrets in `.env`; never place them in frontend code or commit them.

`SPIDERFOOT_*` entries still present in `.env.example` are unused legacy settings and can be ignored.

## Run the API

Start FastAPI:

```bash
cd /Users/chuu/Desktop/shower-hacks
source .venv/bin/activate
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Useful local pages:

- OpenAPI/Swagger UI: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

For predictable offline discovery results, start with fixture mode:

```bash
OSINT_USE_FIXTURES=true INSTAGRAM_USE_FIXTURES=true \
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Fixture usernames include:

- Discovery: `demo-user`
- Instagram public profile: `demo.public`
- Instagram private profile: `demo.private`
- Instagram not found: `demo.missing`
- Instagram unavailable: `demo.unavailable`

## Run the visual frontend

The Next.js frontend is a visual prototype with mocked search results. Run it separately:

```bash
cd /Users/chuu/Desktop/shower-hacks/apps/web
npm install
npm run dev
```

Open <http://localhost:3000>.

## Key API routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Database and provider-configuration status |
| `POST` | `/api/discovery` | Discover public username candidates or inspect a direct URL |
| `POST` | `/api/osint/projects` | Create a project for username-scoped saved public links |
| `GET` | `/api/osint/projects` | List saved-link projects |
| `POST` | `/api/osint/projects/{project_id}/sources` | Save a public URL for a username in an OSINT project |
| `GET` | `/api/osint/projects/{project_id}/sources?username=...` | List saved links for a username |
| `POST` | `/api/projects/{project_id}/sources` | Add a canonical source URL to a corpus project |
| `POST` | `/instagram/profiles` | Look up one Instagram username through Apify or fixtures |
| `POST` | `/api/graph/export` | Export discovery evidence graph data as CSV ZIP or GEXF |
| `POST` | `/api/llm/ping` | Verify the configured LLM returns `LLM_OK` |
| `POST` | `/api/projects/{project_id}/reports` | Generate a source-backed report |
| `POST` | `/api/projects/{project_id}/drafts` | Generate a review-only communication draft |

For complete request and response shapes, use Swagger or see [docs/04-integration-contract.md](docs/04-integration-contract.md).

## Test

Run the full backend suite:

```bash
cd /Users/chuu/Desktop/shower-hacks
source .venv/bin/activate
python -m pytest
```

Run a live LLM connectivity check after configuring `LLM_API_KEY` and `LLM_MODEL`:

```bash
python scripts/llm_ping.py
```

## Project notes

- Discovery, Instagram, crawling, and generation remain separate steps. A discovery result does not automatically become a source or crawl job.
- Communication drafts are AI-generated, require human review, and are never sent by the application.
- The product is designed for public, user-selected sources only. Respect platform terms and applicable law when operating live providers.
