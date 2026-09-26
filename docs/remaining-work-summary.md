# Remaining Work Summary

## Current status

The backend foundation is substantially present. OSINT discovery and Instagram profile extraction exist as API capabilities, but the main frontend and end-to-end workflow are not complete.

## Frontend

- Set up the Next.js/TypeScript frontend runtime; `package.json` is currently empty.
- Build the landing page and project workflow.
- Add username and public-URL input.
- Connect the frontend to discovery, Instagram profile extraction, projects, sources, crawls, reports, and drafts.
- Build the source/corpus view and crawl-progress state.
- Build report, evidence, contradiction, uncertainty, timeline, and draft-review views.
- Add loading, empty, validation, and API-error states.
- Add styling and the intended visual language.
- Add a frontend test runner and component/integration tests.

## OSINT and Instagram

Already present:

- Sherlock, Maigret, and WhatsMyName discovery providers.
- Explicit public-URL discovery.
- Candidate normalization, deduplication, confidence scoring, and fixture mode.
- Manual project/source saving.
- Instagram profile extraction through Apify at `POST /instagram/profiles`.
- Gephi export and a bounded SpiderFoot adapter.

Still needed:

- Connect candidate selection to an explicit crawl allowlist.
- Ensure only approved public URLs reach Firecrawl.
- Decide and enforce how private Instagram profiles are handled in the UI.
- Connect general username discovery to Instagram profile extraction where appropriate.
- Verify live provider behavior with known-good external runs.
- Complete remaining provider failure/configuration tests.

## Crawl and report integration

- Add a worker/background path that executes queued crawls through Firecrawl.
- Connect crawled documents to report generation.
- Connect generated claims and citations to the frontend evidence UI.
- Resolve the documented API contract differences before frontend binding.
- Complete the live personalization adapter; it currently relies on fixtures.

## Verification and delivery

- Add an end-to-end test for:

  `username → discovery → approval → Instagram/profile data or source → crawl → report → evidence view`

- Verify invalid usernames, private profiles, empty results, provider failures, crawl failures, and missing API keys.
- Complete local setup and deployment instructions.
- Run the full test suite and rehearse the demo from a clean restart.

## Recommended order

1. Establish the frontend runtime and basic application shell.
2. Implement username input and Instagram result display.
3. Wire discovery and candidate approval to the source/crawl APIs.
4. Add queued-crawl execution and report integration.
5. Finish evidence, uncertainty, and draft-review screens.
6. Add end-to-end verification and deployment readiness.
