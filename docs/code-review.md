# Code review findings

Review of the repository as of 2026-09-26. Findings are ordered by severity. These are defects and inconsistencies that keep the system from working as one application.

## High

### Chunk indexes break deletes

The FTS5 delete and update triggers in `db/migrations/001_initial.sql` issue a `delete` command without a rowid. SQLite rejects that statement.

After any row exists in `document_chunks`, deleting that chunk, its document, its source, or its project fails with `SQL logic error`, including foreign-key cascades. Inserts and search still work. Tests never delete a chunk, so this path is untested.

### The corpus API and the portrait API do not share data

Two backends sit in the same process and do not talk to each other.

- Projects, sources, crawls, documents, and stored reports live in `data/borrowed_intimacy.db`. Routes are `/projects`, `/sources`, `/crawls`, `/documents`, and `/reports`. Document sensitivity values are `unreviewed`, `clear`, `sensitive`, and `redacted`.
- Discovery, saved links, generation, and graph export use a second SQLite file and `/api/...` routes. Generation only accepts excerpts whose `sensitivityStatus` is `safe`.

`POST /api/projects/{project_id}/reports` and `POST /api/projects/{project_id}/drafts` discard `project_id` and never read stored documents. A request with an empty body returns “No evidence available” even when that project has pages.

`scripts/seed.py` writes the demo project into the corpus database. The test UI at `/` reads the OSINT database, so that demo project never appears there.

`docs/04-integration-contract.md` also lists routes that are not registered:

- `POST /api/projects/{id}/crawls`
- `GET /api/crawls/{id}`
- `GET /api/projects/{id}/corpus`
- `GET /api/reports/{id}`

The crawl routes that exist are `POST /crawls` and `GET /crawls/{id}`.

Queued crawls stay queued. Setting `FIRECRAWL_API_KEY` still raises `FirecrawlNotConfiguredError`. The HTTP API never calls `ingest_scraped_page`.

The two URL normalizers also disagree. Corpus sources use `apps/api/services/urls.py`. Discovery and saved links use `apps/api/services/discovery/normalize.py`. The same public URL can be stored as two different canonical strings.

### The personalization page cannot run

`apps/web/app/personalization/page.tsx` imports `../../lib/personalization-fixtures`. The personalization components import `../../lib/personalization-types`. Those modules are not in the tree. The web app also has no `package.json`, Next.js config, or frontend test runner.

`apps/web/components/personalization/DraftReview.tsx` copies `recipient`, `subject`, and `body` into state on the first render. The page loads the draft afterward, so those fields stay empty once a loader exists.

### WhatsMyName reports profiles that were not confirmed

In `apps/api/services/discovery/providers/whatsmyname.py`, a site counts as a hit when the exists status matches **or** the exists string is present. A 200 response with the required string missing still becomes a candidate.

The HTTP client follows redirects. The private-address check runs before the request, so a redirect onto a loopback or private host is still fetched.

There is no overall deadline. One username query fans out across the whole dataset and can run for several minutes.

## Medium

### `.env` does not configure discovery

`apps/api/config.py` loads `DATABASE_URL` and the LLM fields from `.env`. Sherlock, Maigret, WhatsMyName, `OSINT_USE_FIXTURES`, and `OSINT_DATABASE_URL` are read with `os.getenv`. Nothing calls `load_dotenv`, so those values in `.env` are ignored and the process defaults stay in effect.

The OSINT database path is relative to the process working directory. The corpus database path is anchored at the repository root. Starting the API from another directory uses a different OSINT file than scripts run from the repo root.

### Timeline extraction crashes on dates that only look valid

`apps/api/services/timeline_extractor.py` matches strings such as `2020-13-40` and `February 30, 2020`, then calls `date.fromisoformat` or `strptime`. Those calls raise `ValueError`. One bad excerpt fails the whole timeline.

## Low

### `requirements.txt` cannot install the app

`requirements.txt` lists FastAPI, httpx, python-dotenv, and uvicorn. SQLAlchemy, Pydantic, Pydantic Settings, and the discovery packages are only in `pyproject.toml`. `pip install -e ".[dev]"` is the install path that works.

### Docs disagree with the code

- `docs/03-data-contracts.md` describes sources with `title`, `source_type`, and `status: complete`, and claims with `text`, `claim_type`, and `confidence`. Stored claim rows use `claim_text` and have no confidence.
- `docs/personalization/factual-generation.md` asks for `claim_type` and `source_ids`. The prompts and `validate_claims` require `claimType` and `sourceIds`.
- `README.md` lists Next.js pages, workers, and packages that are not in the repository.
