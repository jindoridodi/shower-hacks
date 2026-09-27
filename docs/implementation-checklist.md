# Three-Team Implementation Checklist

## Shared definition of done

The product is complete when a user can enter a username, review public-source candidates, explicitly approve sources, retrieve permitted public information, generate a source-backed report, and inspect every claim and uncertainty in the frontend.

Core flow:

```text
Username
  → Instagram/profile lookup and OSINT discovery
  → user reviews candidates
  → user explicitly approves sources
  → approved sources enter crawl allowlist
  → public-source retrieval
  → evidence-backed report
  → frontend evidence and review experience
```

## Current status update

The frontend is now present and runnable as a branded prototype. It includes a landing/search experience, local saved profiles, a mock multi-platform result stream, a profile-to-`love-letters` flow, shared styling/assets, and fixture-driven personalization views.

The frontend is not yet connected to the backend: search results are mocked, saved profiles use browser `localStorage`, and the live Instagram, OSINT, crawl, report, and draft APIs are not wired into the main user flow.

## Current execution focus

Teams 2 and 3 are the active implementation teams. Team 1 is considered feature-complete for the prototype and should provide only integration support, API wiring, and verification while Teams 2 and 3 finish the backend workflow.

Priority order:

1. Team 2: stabilize OSINT, Instagram, approval, and allowlist contracts.
2. Team 3: complete crawling, document processing, reports, and operational readiness.
3. Team 1: connect the existing frontend to the finished contracts and verify the end-to-end flow.

## Team 1 — Frontend and UX

### Ownership

Own frontend integration and verification. The prototype UI and visual foundation already exist; remaining work is limited to connecting live contracts, filling only necessary workflow gaps, and testing the completed flow.

### Checklist

- [x] Add a valid frontend `package.json`, TypeScript configuration, and Next.js setup.
- [x] Add development and production build commands.
- [ ] Add frontend API base URL configuration and a typed API client.
- [x] Add application shell, navigation, loading, error, and empty states for the prototype flow.
- [x] Add username/name/profile-link input UI.
- [ ] Replace mocked search results with live discovery and Instagram API calls.
- [ ] Add Instagram lookup through `POST /instagram/profiles`.
- [ ] Display normalized Instagram profile fields, counts, links, posts, verified status, and private status.
- [ ] Add Instagram loading, not-found, unavailable, missing-token, and fixture states.
- [ ] Add OSINT discovery through `POST /api/discovery`.
- [ ] Display candidates, platform, confidence, match reason, provider evidence, and warnings.
- [ ] Explain that discovery suggestions are not identity proof.
- [ ] Add candidate selection, explicit approval, saved-source display, and reject/remove controls.
- [ ] Prevent automatic crawling from the discovery screen.
- [ ] Add project creation and project selection.
- [ ] Add direct public-URL input and crawl-scope review.
- [ ] Display source metadata and queued, running, succeeded, partial, and failed crawl states.
- [ ] Add source ledger and document views.
- [ ] Add report view with claims, confidence, claim types, citations, and evidence drawer.
- [ ] Add contradiction, uncertainty, unknowns, and timeline views.
- [ ] Add communication-draft review with AI-generated and manual-review labels.
- [ ] Do not add send, post, email, calendar, or automatic export actions.
- [ ] Add component test tooling.
- [ ] Test validation, Instagram states, candidate approval, crawl statuses, evidence, reports, drafts, and fixture mode.
- [ ] Confirm the production build succeeds.

### Deliverables

- [x] Runnable frontend application.
- [x] Branded landing/search prototype.
- [x] Local saved-profile prototype.
- [x] Profile-to-`love-letters` prototype flow.
- [x] Fixture-driven personalization views.
- [ ] Typed API client.
- [ ] Live username-to-Instagram UI.
- [ ] OSINT approval UI.
- [ ] Evidence/report UI.
- [ ] Frontend tests and setup notes.

### Reduced priority

- [ ] Do not expand the visual design or add new product surfaces until Teams 2 and 3 finish the live contracts.
- [ ] Do not rebuild the existing landing/search or `love-letters` prototype unless integration reveals a concrete usability issue.

### Dependencies and handoff

- [ ] Receive frozen API contracts and fixtures from Teams 2 and 3.
- [ ] Confirm the private-profile display policy.
- [ ] Replace mock result data and browser-only persistence with the agreed backend contracts.
- [ ] Demonstrate the full frontend in fixture mode.
- [ ] Demonstrate live API connectivity using documented environment variables.
- [ ] Confirm every factual claim has a source link or excerpt.

## Team 2 — OSINT and Instagram

### Ownership

Own public username discovery, Instagram profile extraction, provider behavior, candidate confidence, source approval data, enrichment boundaries, and OSINT safety.

### Checklist

- [ ] Verify Sherlock username discovery.
- [ ] Verify Maigret username discovery.
- [ ] Verify WhatsMyName dataset loading and stale-cache fallback.
- [ ] Preserve explicit public-URL discovery.
- [ ] Normalize and canonicalize candidate URLs.
- [ ] Deduplicate candidates across providers.
- [ ] Calculate confidence from provider evidence.
- [ ] Preserve provider evidence in responses.
- [ ] Return partial results when a provider fails.
- [ ] Return valid empty results for no matches.
- [ ] Add provider timeout and malformed-output handling.
- [ ] Verify subprocesses use argument arrays and never shell execution.
- [ ] Keep fixture mode available for every provider.
- [ ] Verify the `POST /instagram/profiles` contract and Apify actor configuration.
- [ ] Normalize Instagram profile fields and recent caption-bearing posts.
- [ ] Handle Instagram not-found, private, unavailable, and missing-token cases.
- [ ] Decide whether private-profile data is displayed, stored, or discarded.
- [ ] Do not download or analyze images unless separately approved.
- [ ] Add deterministic Instagram fixtures and tests.
- [ ] Define the approved-candidate request and response shape.
- [ ] Save approved URLs to a project and track approval separately from confidence.
- [ ] Ensure rejected candidates cannot be crawled.
- [ ] Ensure only approved URLs enter the crawl allowlist.
- [ ] Prevent discovery from automatically crawling candidates.
- [ ] Verify Gephi CSV ZIP and GEXF exports.
- [ ] Document that OSINT discovery is not identity proof.
- [ ] Run one known-good live username query per provider.
- [ ] Test duplicate results, provider failure, target rejection, timeouts, and fixture/live shape equivalence.

### Deliverables

- [ ] Stable discovery API contract.
- [ ] Stable Instagram profile API contract.
- [ ] Candidate approval and allowlist contract.
- [ ] Provider fixtures and tests.
- [ ] Live-provider verification notes.
- [ ] OSINT safety and privacy notes.

### Dependencies and handoff

- [ ] Receive project/source model requirements from Team 3.
- [ ] Provide discovery and Instagram fixtures to Team 1.
- [ ] Provide approval and allowlist fields to Team 3.
- [ ] Demonstrate that approval is explicit and cannot be bypassed.
- [ ] Demonstrate that public/private status is present and unambiguous.

## Team 3 — Platform, Crawling, Reports, and Operations

### Ownership

Own the database, projects, sources, crawl execution, Firecrawl integration, documents, filtering, report generation, API integration, workers, setup, and deployment.

### Checklist

- [ ] Choose the canonical API route naming convention.
- [ ] Resolve documented versus implemented project/source route differences.
- [ ] Confirm project, source, crawl, document, report, claim, and draft schemas.
- [ ] Confirm crawl statuses, errors, candidate approval, and allowlist fields.
- [ ] Document contracts for Teams 1 and 2.
- [ ] Support project and source creation/retrieval.
- [ ] Validate public URLs and reject credentials, local, private, and invalid targets.
- [ ] Store canonical URLs, approval state, crawl state, timestamps, and content hashes.
- [ ] Prevent duplicate active crawls.
- [ ] Add a worker/background path for queued crawls.
- [ ] Connect the worker to Firecrawl.
- [ ] Enforce allowlist, terms, robots, public-target, and rate-limit checks.
- [ ] Persist crawl start, completion, and failure information.
- [ ] Implement safe transient retries and redirect handling.
- [ ] Create documents from successful crawls.
- [ ] Store raw/cleaned text, chunks, source IDs, and FTS5 records.
- [ ] Deduplicate documents by content hash.
- [ ] Run sensitivity filtering before generation.
- [ ] Prevent sensitive data from entering generation prompts.
- [ ] Return attributable excerpts and empty results instead of invented support.
- [ ] Connect real documents to factual profiles, relationship summaries, and uncertainty reports.
- [ ] Detect and persist contradictions and unknowns.
- [ ] Reject unsupported claims and preserve claim-source relationships.
- [ ] Generate review-only communication drafts with AI labels.
- [ ] Prevent automatic sending or posting.
- [ ] Run the complete Python test suite in a configured environment.
- [ ] Test database, crawl, Firecrawl, documents, filtering, claims, reports, and dependency failures.
- [ ] Complete local setup, deployment, environment, worker, database, and fixture-only documentation.
- [ ] Add health checks for API, database, worker, and required dependencies.
- [ ] Confirm clean restart from an empty database.
- [ ] Confirm logs do not expose credentials or sensitive source content.
- [ ] Add the project license before public release.
- [ ] Rehearse the full demo three times.

### Deliverables

- [ ] Stable backend contracts.
- [ ] Working project/source/crawl APIs.
- [ ] Working crawl worker.
- [ ] Working document and evidence pipeline.
- [ ] Working report and draft generation.
- [ ] Backend and integration tests.
- [ ] Local setup, deployment, and demo documentation.

### Dependencies and handoff

- [ ] Receive the approved-candidate contract from Team 2.
- [ ] Receive frontend API requirements from Team 1.
- [ ] Provide project, source, crawl, report, and draft fixtures to Team 1.
- [ ] Demonstrate that approved sources reach terminal crawl states.
- [ ] Demonstrate that successful crawls create attributable documents.
- [ ] Demonstrate that documents produce cited reports.
- [ ] Demonstrate readable failure behavior when dependencies are unavailable.

## Shared integration milestones

### Milestone 1 — Contract freeze

- [ ] Teams agree on schemas, statuses, errors, fixtures, and environment variables.
- [ ] Team 2 provides discovery and Instagram fixtures.
- [ ] Team 3 provides project, source, crawl, report, and draft fixtures.
- [ ] Team 1 renders all fixture shapes.

### Milestone 2 — Instagram vertical slice

- [ ] User enters a username.
- [ ] Frontend calls the Instagram endpoint.
- [ ] Backend returns normalized profile data or a readable error.
- [ ] Frontend displays profile evidence and public/private status.

### Milestone 3 — OSINT approval slice

- [ ] User enters a username.
- [ ] Providers return candidates.
- [ ] Frontend displays confidence and provider evidence.
- [ ] User explicitly approves a candidate.
- [ ] Approved candidate is saved and allowlisted.

### Milestone 4 — Crawl slice

- [ ] Approved source is queued.
- [ ] Worker executes the crawl.
- [ ] Frontend displays progress and terminal state.
- [ ] Successful crawl creates an attributable document.

### Milestone 5 — Evidence-backed report

- [ ] Documents are filtered and searchable.
- [ ] Report generation returns cited claims.
- [ ] Frontend displays claims, excerpts, contradictions, and unknowns.

### Milestone 6 — Release readiness

- [ ] End-to-end tests pass.
- [ ] Fixture-only demo works from a clean restart.
- [ ] Live dependency failures are readable.
- [ ] Safety checks pass.
- [ ] Setup and deployment documentation is complete.
