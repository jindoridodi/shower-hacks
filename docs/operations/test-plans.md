# Test Plans

Use this file to add automated tests. Each case has an id, the request or action, and the result that must hold. `Status` is `automated` when a current test already covers it, and `gap` when it still needs a test.

Run the backend suite from the repository root:

```bash
python3 -m pytest
```

Corpus errors use `{"detail": {"code", "message"}}`. OSINT routes that raise `HTTPException` put a string in `detail`. The corpus database is `data/borrowed_intimacy.db`. OSINT projects and manual sources use `OSINT_DATABASE_URL`, default `sqlite:///./data/osint_sources.db`. Do not mix those databases in one assertion.

Crawl statuses are `queued`, `running`, `succeeded`, and `failed`. `complete` and `partial` are not crawl statuses. `partial` on `POST /api/discovery` is a provider-failure boolean.

Firecrawl scrapes approved public pages. Apify is only `POST /instagram/profiles`. Tests must not call either network API. Patch the scraper or use `OSINT_USE_FIXTURES=true`.

This file lists behavior the app has now. Section 8 lists product goals that are not built. Do not automate those as passing tests until the code exists.

## 1. Corpus, crawls, and persisted reports

| ID | Status | Action | Expected |
|---|---|---|---|
| CORP-01 | automated | `POST /projects`, then `POST /sources` with a public URL | `201`. Stored URL is canonical. `tests/test_sources.py` |
| CORP-02 | automated | Same canonical URL twice in one project | Second create is rejected. The same URL may exist in another project. |
| CORP-03 | automated | `http://` and `https://` for the same host and path | Two sources. |
| CORP-04 | automated | Credential, non-http, or malformed URL | `422`, code `validation_error` or `invalid_url`. No source row. |
| CORP-05 | automated | `POST /sources/{id}/queue` twice, including concurrent calls | One job is `queued` or `running`. The other is `409` `crawl_already_active`. |
| CORP-06 | automated | `PATCH /crawls/{id}` with status `complete` or `partial` | `422` `validation_error`. |
| CORP-07 | automated | Move a job through `queued` → `running` → `succeeded` and → `failed` | Timestamps update. `scraped_at` is set only on success. A succeeded job cannot carry `error_message`. |
| CORP-08 | automated | Ingest a `ScrapedPage`, then ingest the same cleaned text again | Document `content_hash` matches the cleaned text. The second response is deduplicated and `source.content_hash` is updated. |
| CORP-09 | automated | Add chunks and `GET /search/chunks?q=` | Matching chunk text is returned. Blank chunk text is rejected. |
| CORP-10 | automated | `POST /api/projects/{id}/reports/persisted` with cited excerpts | `201` on create, `200` on the same report again. Rows exist in `reports`, `report_claims`, and `claim_sources`. Retry does not duplicate `(claim_id, source_id, excerpt)`. |
| CORP-11 | automated | Persist an `unknown` claim with no source ids | Claim row exists. It has zero `claim_sources` rows. |
| CORP-12 | automated | Missing excerpt, source from another project, or sensitive/redacted evidence | Persistence fails. No partial report remains. |
| CORP-13 | automated | Delete a source that is cited | Database rejects the delete. |
| CORP-14 | automated | `GET /api/reports/{id}` and `GET /reports/{id}` | Same body. |
| CORP-15 | automated | `POST /api/projects/{id}/reports` with `useFixtures: true` | JSON only. No new corpus report row. |
| CORP-16 | gap | `POST /api/projects/{id}/crawls` with a source from another project | `409`. No new crawl job. |
| CORP-17 | automated | `GET /api/projects/{id}/corpus` after a document and chunks exist | Sources, documents, and chunks for that project only. `tests/test_documents.py` |
| CORP-18 | automated | Create claims concurrently | Positions are unique. `tests/test_claims.py` |
| CORP-19 | automated | Persist `observed`, `inferred`, or `uncertain` with no `sourceIds` | Rejected. No report row. `tests/test_report_persistence.py` |
| CORP-20 | automated | Persist a report that includes `contradictions` and `generatedAt` | Claims and excerpts are stored. Those two fields are not written to SQLite. `tests/test_report_persistence.py` |

`tests/test_backend_integration.py` is the flow test for CORP-01 through CORP-14: project, public source, queued crawl, ingested page, hash, deduped document, searchable chunk, persisted claim, exact excerpt.

## 2. Document filtering and Firecrawl

Patch `PublicPageScraper`. Do not set `FIRECRAWL_API_KEY` in these tests.

| ID | Status | Action | Expected |
|---|---|---|---|
| DOC-01 | automated | Ingest a page that contains an email or password | Filtering runs before any insert. Stored text omits the rejected value. `GET /search/chunks` for that value returns `[]`. |
| DOC-02 | automated | Ingest a page with nothing usable left | Job is `failed`. No document row and no FTS row. |
| DOC-03 | automated | Chunk insert fails after the document insert | Document, source, job, and FTS changes roll back together. |
| DOC-04 | automated | Scraper raises | Job is `failed`. Stored `error_message` has no credentials and no sensitive page text. |
| DOC-05 | automated | Ingest a page whose URL does not canonicalize to the source URL | Job status is unchanged. |
| DOC-06 | automated | Call the scraper with no `FIRECRAWL_API_KEY` | No network call. `FirecrawlNotConfiguredError`. |
| DOC-07 | gap | Configured scraper receives a URL outside `CRAWL_ALLOWED_URLS` or `CRAWL_TERMS_ACCEPTED_HOSTS` | `FirecrawlPolicyError`. No scrape request is sent. |
| DOC-08 | automated | Apply migrations, including `003_document_processing`, twice | Second run applies nothing. Existing documents survive the new columns. `db/schema.sql` equals the sorted files in `db/migrations`. |
| DOC-09 | gap | `robots.txt` disallows the URL, or robots.txt cannot be fetched | `FirecrawlPolicyError`. No scrape request is sent. |
| DOC-10 | gap | Host resolves to a loopback or private address | `FirecrawlPolicyError`. No scrape request is sent. |
| DOC-11 | automated | `GET /search/chunks` across two projects, including a filtered document | Results stay inside the requested scope and limit. Filtered evidence is absent. `unreviewed` documents remain searchable. `tests/test_retrieval.py` |
| DOC-12 | gap | Successful ingest | `documents.raw_path` points at the written markdown file. `document_chunks.embedding` stays null. |

## 3. OSINT discovery and approval

Set `OSINT_USE_FIXTURES=true` unless the case says live. Approval writes the corpus database. Discovery and manual sources write the OSINT database.

| ID | Status | Action | Expected |
|---|---|---|---|
| OSINT-01 | automated | `POST /api/discovery` with `{"query":"demo-user"}` | Fixture candidates. Camel-case fields. |
| OSINT-02 | automated | `POST /api/discovery` with an unknown username | `200` and an empty candidate list. |
| OSINT-03 | automated | `POST /api/discovery` with a public `https://` URL | One high-confidence candidate. |
| OSINT-04 | automated | Discovery or normalize with a local, private, or non-http target | Request rejected. No candidate stored. |
| OSINT-05 | gap | One provider raises while another returns a candidate | `partial` is `true`. A warning is present. The successful candidate is still returned. |
| OSINT-06 | automated | `POST /api/projects`, then `POST /api/projects/{id}/sources` with a public URL | `201`. A later discovery for that username and `projectId` includes the saved URL. |
| OSINT-07 | automated | Repeat OSINT-06 for the same URL | Duplicate is rejected. `DELETE` removes it. |
| OSINT-08 | automated | `POST /api/approvals` with a corpus `projectId`, matching username, and public candidate | `201`. One corpus `sources` row with status `pending` and one `source_approvals` row. Crawl job count stays `0`. |
| OSINT-09 | automated | `candidateUsername` does not match `username` | `422`. No source row. |
| OSINT-10 | automated | Approve the same canonical URL again | `409` `duplicate_canonical_url`. |
| OSINT-11 | gap | `POST /api/approvals` with an unknown `projectId` or an unsafe URL | `404` or `422` `invalid_url`. No source and no crawl. |
| OSINT-12 | automated | `GET /api/approvals?projectId=` | Lists only approvals for that corpus project. |
| OSINT-13 | automated | `POST /api/graph/export` for `csv` and `gexf` | CSV zip has the Gephi tables. GEXF is valid XML. |
| OSINT-14 | automated | SpiderFoot with a non-local URL, a disallowed module, or a private result URL | Rejected. Results are not inserted as crawl sources. |
| OSINT-15 | gap | Live Sherlock, Maigret, and WhatsMyName, one known public username, `OSINT_USE_FIXTURES=false` | Each provider returns or fails visibly. The process is not started through a shell string. Keep this out of the default `pytest` run. |

## 4. Instagram

Patch the Apify client. Do not send a real `APIFY_API_TOKEN` in the default suite.

| ID | Status | Action | Expected |
|---|---|---|---|
| IG-01 | automated | Scraper returns a public profile payload | `POST /instagram/profiles` is `200`. Profile fields and at most 10 caption-bearing posts are normalized. Image values stay URLs. |
| IG-02 | automated | No `APIFY_API_TOKEN` | `503` `apify_not_configured`. |
| IG-03 | automated | Actor payload is an error row, or the username is invalid | Stable error status. No corpus source and no crawl job. |
| IG-04 | gap | Profile is private | Response exposes the private status. No caption content is stored as evidence, and no crawl source is created. |
| IG-05 | gap | One live call with a public demo account | Response matches the fixture shape. Logs do not contain the token. Keep this out of the default `pytest` run. |

## 5. Frontend

`apps/web` tests run with Playwright: `npm test` from `apps/web`. Search is still mocked, so a passing UI test does not prove the API was called. The name, username, and link cards are labels. WEB-02 types those example values.

| ID | Status | Action | Expected |
|---|---|---|---|
| WEB-01 | automated | Open `/` | Heading is visible. The search box is empty. **peek!** is disabled. `apps/web/e2e/frontend.spec.ts` |
| WEB-02 | automated | Type the Name, Username, and Link examples | The box fills and **peek!** becomes enabled. The cards themselves are labels. |
| WEB-03 | automated | Submit a known mock query | Mock accounts render. No request is sent to `/api/discovery`, `/instagram/profiles`, `/crawls`, or `/reports`. |
| WEB-04 | automated | Submit an empty query | **peek!** stays disabled. No crawl or report request is sent. |
| WEB-05 | automated | Save a profile, reload `/` | The profile is listed under saved profiles. It is in `localStorage`. |
| WEB-06 | automated | Open `/love-letters` and generate a letter | The letter is visible and labeled AI-generated and review-only. No post, email, or export control. |
| WEB-07 | automated | Open a claim that has an excerpt | The excerpt text is visible. |
| WEB-08 | automated | Load `/` at a narrow viewport | Search, results, and saved profiles remain usable. |
| WEB-09 | automated | Open `/personalization` with fixtures on | Claims show type, confidence, and an evidence excerpt. A year-only timeline event is separate from a full date. The draft is editable, labeled AI-generated, and says review is required. No send, post, email, export, or calendar control. |
| WEB-10 | automated | Call `loadPersonalizationData` with `NEXT_PUBLIC_USE_FIXTURES=false` | The live-adapter error is thrown. No fixture content is returned. |
| WEB-11 | automated | Open `/persona` | Redirects to `/love-letters`. |
| WEB-12 | automated | Generate a letter on `/love-letters` | The sample letter renders on the page. No API request is sent. |

`/ingest`, `/generate`, `/reveal`, and `/corpus/[id]` are empty pages. Do not write behavior tests for them until they render a flow.

## 6. Generation, drafts, and timeline

These functions take excerpts from the caller. They do not read the corpus database by themselves.

| ID | Status | Action | Expected |
|---|---|---|---|
| GEN-01 | automated | Generate with one `safe` excerpt and one `restricted` or `sensitive` excerpt | The prompt and the returned report contain only the `safe` excerpt. If nothing `safe` remains, claims are empty, an unknown is returned, and the model is not called. `tests/test_report_generator.py` |
| GEN-02 | automated | Generate with empty evidence | Title `No evidence available`. No invented claim. |
| GEN-03 | automated | Validate a claim with a missing source id, an unknown source id, an observed inference, or a quote that is not in the evidence | Rejected. `tests/test_claim_validation.py` |
| GEN-04 | automated | Draft generator in fixture mode | Draft includes the AI-generated label and `reviewRequired: true`. `tests/test_communication_draft_generator.py` |
| GEN-05 | automated | Draft output missing the label, with `reviewRequired: false`, or citing an unknown source | Rejected. |
| GEN-06 | automated | Draft with empty evidence | Review-only draft. No invented recipient content. |
| GEN-07 | automated | `POST /api/projects/{id}/drafts` | Response is JSON. No corpus row is written, and the model client is not constructed. `tests/test_communication_draft_generator.py` |
| GEN-08 | automated | Extract timeline dates | A written month date is normalized. A year-only or ambiguous numeric date stays unnormalized. Restricted evidence is ignored. Empty evidence returns no items. `tests/test_timeline_extractor.py` |
| GEN-09 | gap | `POST /api/llm/ping` with no model key | Readable error. The key is not included in the response body. |

## 7. Demo path

This is the sequence to automate once the UI calls the API. Until then, keep the API portion in `tests/test_backend_integration.py` and run the UI portion from section 5 separately.

1. Reset with `python scripts/reset_db.py` and start the API with `OSINT_USE_FIXTURES=true`.
2. `POST /api/discovery` for `demo-user`, then `POST /api/approvals` for one public candidate.
3. Assert one corpus source and zero crawl jobs.
4. Queue that source and run the crawl with a fixture `ScrapedPage`.
5. Assert the job is `succeeded`, the document has a content hash, and chunk search hits the page text.
6. Persist a fixture report and `GET /api/reports/{id}`. The excerpt matches the fixture exactly.
7. Repeat ingest with a page that contains an email. Search for that email returns `[]`.
8. Restart the API process. The same report and document are still readable.

Seed twice with `python scripts/seed.py` and assert one project named `Demo`. Reset must refuse every database path other than `data/borrowed_intimacy.db`.

## 8. Not built yet

Do not add these as tests that are expected to pass today.

| Goal | Why it is not a current test |
|---|---|
| Username on the landing page calls discovery and Instagram | `/` still renders mock accounts and saves profiles in `localStorage`. |
| Approval puts a URL on the Firecrawl allowlist | `POST /api/approvals` creates a corpus source. `CRAWL_ALLOWED_URLS` is separate configuration. |
| A background worker drains the crawl queue | `run_queued_crawl` runs only when a caller invokes it. |
| Report generation reads stored documents on its own | The generator uses the excerpts passed into the call. |
| Contradictions are stored and shown | Persistence ignores `contradictions`. |
| Private Instagram policy | The endpoint does not yet define what a private profile returns. |
| `/ingest`, `/generate`, `/reveal`, `/corpus/[id]` | Those page files are empty. |
