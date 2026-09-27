# freakypeeky

<p align="center">
  <img src="apps/web/public/banner.png" alt="freakypeeky banner" width="480" />
</p>

freakypeeky is a web-art prototype that turns selected public web material into a source-linked portrait experience. It has public username discovery, Instagram profile lookup, a SQLite-backed source/corpus API, and source-grounded AI reports and drafts.

Discovery results are suggestions, not identity proof. The app does not log in to accounts, bypass access controls, download Instagram media, or automatically crawl a discovered link.

## Quick start

The default path uses live providers. Add the credentials for the capabilities you want, then start the API and frontend.

### 1. Install

Requirements: Python 3.11+ and Node.js 20+.

```bash
cd freakypeeky
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,osint]'
cp .env.example .env
python scripts/migrate.py
```

### 2. Configure live providers

Edit `.env`. Configure only the providers you intend to use:

| Feature | Required configuration |
| --- | --- |
| Live username discovery | `OSINT_USE_FIXTURES=false`; Sherlock and Maigret are installed through the `osint` extra. |
| Live Instagram profile lookup | `APIFY_API_TOKEN`, `APIFY_INSTAGRAM_ACTOR=apify~instagram-profile-scraper`, and `INSTAGRAM_USE_FIXTURES=false` |
| Live LLM reports and drafts | `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` |
| Local embeddings | `EMBEDDINGS_ENABLED=true`, plus `pip install -e '.[embeddings]'` |

Keep secrets in `.env`; do not commit them or put them in frontend code.

### 3. Start the live API

Keep this terminal open:

```bash
cd freakypeeky
source .venv/bin/activate
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Open the API explorer at <http://127.0.0.1:8000/docs>.

| Route | Request body | Expected result |
| --- | --- | --- |
| `POST /api/discovery` | `{"query":"openai"}` | Public username candidates, provider warnings when applicable |
| `POST /instagram/profiles` | `{"username":"nasa"}` | Public profile when Apify is configured |
| `POST /api/llm/ping` | none | `LLM_OK` when the LLM is configured |

Health: <http://127.0.0.1:8000/api/health>

### 4. Start the freakypeeky frontend

In a second terminal:

```bash
cd freakypeeky/apps/web
npm install
npm run dev
```

Open <http://localhost:3000>.

> The Next.js frontend is currently a visual prototype: its search and personalization views use mock or fixture data. Use Swagger at port `8000` to test the live backend until frontend/API wiring is complete.

## Fixture mode

Use fixtures for offline work, repeatable demos, or when live providers are unavailable. Restart Uvicorn with:

```bash
cd freakypeeky
source .venv/bin/activate
OSINT_USE_FIXTURES=true INSTAGRAM_USE_FIXTURES=true \
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

| Route | Request body | Expected result |
| --- | --- | --- |
| `POST /api/discovery` | `{"query":"demo-user"}` | Deterministic public URL candidates |
| `POST /instagram/profiles` | `{"username":"demo.public"}` | Public fixture profile with posts |
| `POST /instagram/profiles` | `{"username":"demo.private"}` | Private fixture profile with protected fields omitted |
| `POST /instagram/profiles` | `{"username":"demo.missing"}` | `404 instagram_profile_not_found` |

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| API | Python 3.11, FastAPI, Pydantic, SQLAlchemy |
| Database and search | SQLite and FTS5 |
| Public discovery | Sherlock, Maigret, WhatsMyName |
| Instagram | Apify `apify/instagram-profile-scraper` |
| AI generation | OpenAI-compatible chat-completions API |
| Graph export | NetworkX to CSV ZIP or GEXF |
| Testing | pytest and Playwright |

## What is implemented

| Area | Available now |
| --- | --- |
| Discovery | Sherlock, Maigret, WhatsMyName, direct URL normalization, confidence/evidence, fixtures, and CSV ZIP/GEXF graph export |
| Manual public links | Username-scoped OSINT projects and saved public URLs in SQLite |
| Instagram | Apify adapter, public/private normalization, deterministic fixtures, and stable error states |
| Corpus | Projects, canonical sources, approvals, crawl jobs, documents, chunks, FTS search, reports, and citations |
| Generation | OpenAI-compatible LLM adapter, factual/uncertainty reports, review-only communication drafts, and LLM ping |
| Frontend | Next.js visual prototype and fixture-driven personalization screens |

## API map

The full contract is in [docs/04-integration-contract.md](docs/04-integration-contract.md). These routes are the usual starting points:

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Confirm database and provider configuration |
| `POST` | `/api/discovery` | Find public username candidates or validate a direct URL |
| `POST` | `/api/osint/projects` | Create an OSINT project for saved username links |
| `GET` | `/api/osint/projects` | List OSINT projects |
| `POST` | `/api/osint/projects/{project_id}/sources` | Save `{ "username", "url" }` as a public manual link |
| `GET` | `/api/osint/projects/{project_id}/sources?username=...` | List saved links for one username |
| `POST` | `/instagram/profiles` | Retrieve one Instagram profile through Apify or fixtures |
| `POST` | `/api/graph/export?format=csv` | Download a CSV ZIP evidence graph; use `format=gexf` for Gephi |
| `POST` | `/api/llm/ping` | Check that the configured LLM returns `LLM_OK` |
| `POST` | `/api/projects/{project_id}/reports` | Generate and persist a source-backed report |
| `POST` | `/api/projects/{project_id}/drafts` | Generate a review-only communication draft |

## Test

```bash
cd freakypeeky
source .venv/bin/activate
python -m pytest
```

Verify a configured live LLM without exposing its key:

```bash
python scripts/llm_ping.py
```

## Project layout

```text
apps/api/             FastAPI routes, services, schemas, and database wiring
apps/web/             Next.js frontend prototype
data/fixtures/        Deterministic discovery, Instagram, report, and draft fixtures
db/migrations/        SQLite schema migrations
packages/prompts/     Structured prompts for reports and drafts
scripts/              Migration, seed, reset, import, and LLM-ping commands
tests/                Backend, generation, ingestion, and persistence tests
docs/                 API contracts, plans, runbooks, and team handoffs
```

## Important boundaries

- The OSINT saved-link store and corpus/source workflow are separate SQLite-backed slices that still need end-to-end consolidation.
- A discovery result, Instagram lookup, or generated graph never automatically creates a crawl job.
- Private Instagram responses contain only limited metadata. Biography, image, external URL, category, and posts are omitted.
- Communication drafts are AI-generated, require human review, and are never sent by the application.
- Use only public, user-selected sources and respect platform terms and applicable law.
