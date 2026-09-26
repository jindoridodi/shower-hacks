# Borrowed Intimacy Implementation Checklist

## Definition of done

The product is complete when a user can enter a username, review public-source candidates, explicitly approve sources, retrieve permitted public information, generate a source-backed report, and inspect every claim and uncertainty in the frontend.

The Instagram path must support:

```text
Instagram username
  → profile lookup
  → public/private status
  → normalized profile data
  → frontend review
```

The broader OSINT path must support:

```text
Username
  → candidate discovery
  → confidence and provider evidence
  → explicit user approval
  → crawl allowlist
  → public-source retrieval
  → evidence-backed report
```

## Phase 0 — Confirm scope and contracts

### Checklist

- [ ] Confirm the primary demo flow: username input, Instagram lookup, OSINT discovery, or all three.
- [ ] Choose the canonical frontend API base URL.
- [ ] Choose one API naming convention for projects, sources, crawls, reports, and claims.
- [ ] Confirm source states and crawl states.
- [ ] Confirm the policy for private Instagram profiles.
- [ ] Confirm which fields are safe to display and persist.
- [ ] Confirm whether Instagram data is only displayed or also included in generated reports.
- [ ] Choose one prepared demo username and one fallback fixture username.
- [ ] Document required credentials: Apify, Firecrawl, and LLM provider.

### Exit criteria

- [ ] Frontend and backend owners agree on request and response shapes.
- [ ] The demo path can be described in one short sequence without ambiguous steps.
- [ ] No feature depends on an unresolved privacy or authorization decision.

## Phase 1 — Make the frontend runnable

### Checklist

- [ ] Add a valid frontend `package.json`.
- [ ] Add Next.js, React, TypeScript, and the selected styling dependencies.
- [ ] Add `tsconfig.json` and required Next.js configuration.
- [ ] Add a frontend development command.
- [ ] Add a frontend production build command.
- [ ] Add the frontend API base URL configuration.
- [ ] Add a shared API client with typed request and response helpers.
- [ ] Add a shared application shell and navigation.
- [ ] Add a global loading state.
- [ ] Add a global error state.
- [ ] Add a consistent empty state.
- [ ] Confirm the frontend starts cleanly against a local API.

### Exit criteria

- [ ] The frontend opens at the expected local URL.
- [ ] The frontend can call `/health` or `/api/health`.
- [ ] A production build completes successfully.

## Phase 2 — Username and Instagram experience

### Checklist

- [ ] Add a username input with validation matching the backend.
- [ ] Add an Instagram lookup action.
- [ ] Call `POST /instagram/profiles`.
- [ ] Show loading, not-found, unavailable, and missing-token states.
- [ ] Display username, full name, biography, profile URL, category, and external URL.
- [ ] Display follower, following, and post counts when available.
- [ ] Display verified and private status clearly.
- [ ] Do not present private-profile data as public evidence.
- [ ] Display recent caption-bearing posts only when returned.
- [ ] Link each displayed public profile or post to its source URL.
- [ ] Add fixture mode for the Instagram path.
- [ ] Add a clear distinction between retrieved facts and interpretation.
- [ ] Decide whether profile results are persisted to a project or remain transient.

### Exit criteria

- [ ] A valid username produces a readable Instagram result in the frontend.
- [ ] An invalid username produces a useful validation message.
- [ ] Missing `APIFY_API_TOKEN` produces a useful configuration message.
- [ ] A private or unavailable profile is handled according to the approved policy.
- [ ] The flow works without live credentials in fixture mode.

## Phase 3 — OSINT discovery and approval

### Checklist

- [ ] Add username discovery input to the frontend.
- [ ] Call `POST /api/discovery`.
- [ ] Display candidate URL, platform, confidence, match reason, and provider evidence.
- [ ] Display partial-provider warnings without hiding successful results.
- [ ] Distinguish discovery suggestions from verified identity.
- [ ] Add candidate selection controls.
- [ ] Add an explicit approval action.
- [ ] Save approved URLs to the selected project.
- [ ] Display already-saved sources.
- [ ] Add remove/reject controls for saved candidates.
- [ ] Prevent automatic crawling during discovery.
- [ ] Ensure only approved URLs enter the crawl allowlist.
- [ ] Handle duplicate candidates deterministically.
- [ ] Handle zero candidates cleanly.
- [ ] Handle provider timeout and unavailable states cleanly.
- [ ] Keep fixture mode available for all providers.

### Exit criteria

- [ ] A username returns ranked candidates in the frontend.
- [ ] The user must explicitly approve a candidate before crawling.
- [ ] A rejected candidate is not queued for crawling.
- [ ] Candidate provider evidence is visible to the user.

## Phase 4 — Projects, sources, and crawl workflow

### Checklist

- [ ] Add project creation and project selection.
- [ ] Add public URL input as a separate direct-input path.
- [ ] Validate public URLs before saving.
- [ ] Reject credentials, loopback, private, and invalid URL targets.
- [ ] Create source records through the API.
- [ ] Display source status and canonical URL.
- [ ] Add a crawl-scope review before starting.
- [ ] Add an explicit queue/start crawl action.
- [ ] Display queued, running, succeeded, partial, and failed states consistently.
- [ ] Add crawl error details without exposing sensitive internals.
- [ ] Add a worker/background execution path for queued crawls.
- [ ] Connect the worker to the Firecrawl scraper.
- [ ] Enforce allowlist, terms, robots, public-target, and rate-limit checks.
- [ ] Persist crawl timestamps, errors, and content hashes.
- [ ] Add retry behavior for safe transient failures.
- [ ] Prevent duplicate active crawls for the same source.

### Exit criteria

- [ ] An approved source can be queued from the frontend.
- [ ] A queued crawl reaches a terminal state.
- [ ] A successful crawl creates a document.
- [ ] A failed crawl is visible and recoverable.
- [ ] No unapproved URL is fetched.

## Phase 5 — Documents, evidence, and report generation

### Checklist

- [ ] Display the source ledger for a project.
- [ ] Display document title, URL, capture time, and processing status.
- [ ] Display searchable or selectable document excerpts.
- [ ] Preserve source IDs through chunks, retrieval, claims, and UI components.
- [ ] Add sensitivity filtering before generation.
- [ ] Ensure sensitive data is not passed into generation.
- [ ] Generate a factual profile with citations.
- [ ] Generate a relationship summary with citations.
- [ ] Generate an uncertainty report.
- [ ] Detect and display contradictions.
- [ ] Display unknowns when the corpus lacks support.
- [ ] Reject unsupported claims.
- [ ] Label observed facts, inferences, uncertainty, and conflicts.
- [ ] Make every claim link to one or more source excerpts.
- [ ] Add report loading, empty, failed, and unavailable-model states.
- [ ] Connect the existing report-generation API to the frontend.

### Exit criteria

- [ ] A report cannot contain an unsupported factual claim.
- [ ] Every displayed claim has a usable source link or excerpt.
- [ ] Empty evidence produces no fabricated claims.
- [ ] Conflicting evidence is shown rather than silently resolved.

## Phase 6 — Evidence reveal and communication draft review

### Checklist

- [ ] Add a claim detail/evidence drawer.
- [ ] Add source excerpt highlighting or clear excerpt presentation.
- [ ] Add confidence display with the documented meanings.
- [ ] Add the public timeline view.
- [ ] Separate precise and imprecise dates.
- [ ] Add communication-draft generation through the backend.
- [ ] Display recipient, subject, and body as editable fields.
- [ ] Display the exact AI-generated label.
- [ ] Display the manual-review requirement.
- [ ] Keep citations attached to draft claims where applicable.
- [ ] Do not add send, post, email, calendar, or automatic export actions.
- [ ] Ensure drafts never imitate the subject's voice or conceal AI authorship.

### Exit criteria

- [ ] A user can move from a claim to its evidence in one interaction.
- [ ] A user can review and edit a draft without any automatic external action.
- [ ] The UI clearly separates evidence from generated language.

## Phase 7 — OSINT extensions and optional enrichment

### Checklist

- [ ] Verify Sherlock behavior with a live known-good query.
- [ ] Verify Maigret behavior with a live known-good query.
- [ ] Verify WhatsMyName dataset loading and stale-cache fallback.
- [ ] Confirm provider failures remain non-fatal.
- [ ] Add complete subprocess timeout and malformed-output coverage.
- [ ] Verify Gephi CSV ZIP output manually.
- [ ] Verify GEXF output opens in Gephi.
- [ ] Keep SpiderFoot disabled unless explicitly configured.
- [ ] Enforce the SpiderFoot module allowlist.
- [ ] Enforce local-sidecar restrictions.
- [ ] Cap enrichment result counts.
- [ ] Require explicit user selection before any enrichment result can become a crawl source.
- [ ] Document that OSINT discovery is not identity proof.

### Exit criteria

- [ ] Every live provider can be replaced by deterministic fixtures.
- [ ] One failed provider does not block the remaining providers.
- [ ] Enrichment cannot silently trigger crawling or profile contact.

## Phase 8 — Testing and safety verification

### Backend tests

- [ ] Run all Python tests in a configured virtual environment.
- [ ] Test username validation.
- [ ] Test URL validation and canonicalization.
- [ ] Test provider deduplication and confidence scoring.
- [ ] Test provider timeout and unavailable behavior.
- [ ] Test private/local target rejection.
- [ ] Test explicit candidate approval and allowlisting.
- [ ] Test crawl state transitions.
- [ ] Test crawl failure persistence.
- [ ] Test document hash and deduplication behavior.
- [ ] Test sensitivity filtering.
- [ ] Test claim-source integrity.
- [ ] Test report generation with empty evidence.
- [ ] Test Instagram success, not-found, private, invalid, and unconfigured cases.

### Frontend tests

- [ ] Add component test tooling.
- [ ] Test username validation.
- [ ] Test Instagram loading, success, and error states.
- [ ] Test candidate selection and approval.
- [ ] Test source and crawl status rendering.
- [ ] Test evidence drawer behavior.
- [ ] Test contradiction and unknown displays.
- [ ] Test draft review labels and disabled external actions.
- [ ] Test fixture mode.

### Manual safety checks

- [ ] Verify no credentials or cookies are accepted for scraping.
- [ ] Verify no private-account content is presented as public evidence.
- [ ] Verify no candidate is crawled automatically.
- [ ] Verify no generated message is sent automatically.
- [ ] Verify sensitive fields are filtered before generation.
- [ ] Verify source URLs and excerpts remain attributable.

## Phase 9 — Operations and release

### Checklist

- [ ] Complete local setup instructions.
- [ ] Add frontend environment configuration documentation.
- [ ] Add API URL and CORS configuration documentation.
- [ ] Document Apify, Firecrawl, and LLM setup.
- [ ] Document fixture-only startup.
- [ ] Add database initialization and reset instructions.
- [ ] Add worker startup instructions.
- [ ] Add SpiderFoot optional-service instructions.
- [ ] Add production secrets configuration.
- [ ] Add health checks for frontend, API, database, and worker.
- [ ] Confirm clean restart from an empty local database.
- [ ] Confirm the demo works without live credentials in fixture mode.
- [ ] Run the complete demo three times.
- [ ] Verify logs do not expose sensitive source content or credentials.
- [ ] Add the project license before public release.

### Exit criteria

- [ ] A new developer can start the system from the documentation.
- [ ] The demo can complete in under two minutes with fixtures.
- [ ] The live path fails clearly when credentials or services are unavailable.
- [ ] The release scope and known limitations are documented.

## Recommended execution order

### Milestone 1 — Runnable shell

Complete Phases 0–1. The frontend starts, builds, and can reach the API.

### Milestone 2 — Instagram vertical slice

Complete Phase 2. A user can enter an Instagram username and inspect normalized profile information, including private/unavailable states.

### Milestone 3 — OSINT approval slice

Complete Phase 3. A user can discover candidates, understand confidence/provider evidence, and explicitly approve sources.

### Milestone 4 — Crawl slice

Complete Phase 4. Approved sources can be crawled and produce stored documents with visible status.

### Milestone 5 — Evidence-backed report

Complete Phase 5. Stored documents become cited claims, contradictions, and unknowns in the frontend.

### Milestone 6 — Finished experience

Complete Phase 6. Evidence reveal, timeline, and review-only communication drafts are usable.

### Milestone 7 — Harden and release

Complete Phases 7–9. Live providers, tests, safety constraints, operations, and demo rehearsal are complete.

## Highest-priority blockers

1. Frontend runtime and application shell are not established.
2. Frontend-to-API integration is not implemented.
3. Candidate approval is not yet connected to a crawl allowlist.
4. Queued crawl execution is not wired to a worker.
5. Live personalization/report data is not connected; the current UI is fixture-driven.
6. The full test suite cannot currently be verified until the Python test environment is available.
