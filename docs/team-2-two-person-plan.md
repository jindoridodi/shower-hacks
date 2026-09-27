# Team 2: OSINT and Instagram Two-Person Plan

## Team 2 outcome

Team 2 is done when the system can safely turn a username into:

```text
public discovery candidates and/or Instagram profile data
  → clear source and confidence information
  → explicit user approval
  → a defined handoff to Team 3's crawlable source workflow
```

Team 2 does not crawl candidates, generate reports, or build new frontend screens. Team 1 owns the UI integration; Team 3 owns the canonical crawl/source database and worker.

## Current state

Already implemented:

- Sherlock, Maigret, and WhatsMyName discovery providers.
- Public URL normalization, deduplication, confidence scoring, warnings, and fixture mode.
- An Instagram profile endpoint backed by Apify.
- A separate OSINT project/source store for manually saved public URLs.
- Gephi export.
- Unit tests for core provider parsing and Instagram normalization.

Important integration gap:

The OSINT project/source store is separate from Team 3's main project/source/crawl database. A selected candidate is not yet a canonical source eligible for Team 3's crawl workflow.

## Division of ownership

| Area | Person A | Person B |
| --- | --- | --- |
| Discovery providers | Own | Review/test |
| Candidate approval contract | Own | Review |
| Team 3 source handoff | Joint design, A implements Team 2 side | Joint design, B verifies integration |
| Instagram/Apify endpoint | Review/test | Own |
| Private-profile policy | Joint decision | Joint decision |
| Fixtures | Discovery fixtures | Instagram fixtures |
| Tests | Discovery/approval tests | Instagram/live-config tests |
| Gephi | Own | Review/test |
| Team 1 handoff | Discovery contract | Instagram contract |

## Step 0 — Joint contract freeze

Both people complete this before changing implementation code.

- [ ] Read the existing discovery, manual-source, Instagram, source, and crawl route contracts.
- [ ] Identify the two project/source stores and document their ownership.
- [ ] Agree that Team 3's source/crawl database is the canonical destination for approved crawl sources.
- [ ] Define the candidate-approval payload.
- [ ] Define the response returned after approval.
- [ ] Decide whether a duplicate approval is idempotent or returns a conflict.
- [ ] Decide the private Instagram policy.
- [ ] Agree on fixture names and locations.
- [ ] Share final field names with Teams 1 and 3 before implementation begins.

### Required approval contract

The contract should contain at least:

```json
{
  "projectId": "canonical-team-3-project-id",
  "username": "public_username",
  "candidate": {
    "url": "https://example.com/public-profile",
    "platform": "example",
    "candidateUsername": "public_username",
    "confidence": "medium",
    "matchReason": "Provider found an exact public username match."
  },
  "providerEvidence": ["sherlock", "maigret"]
}
```

The result must identify the canonical Team 3 source record and preserve the selection/provenance needed by the UI.

### Exit gate

- [ ] Team 1 can build against fixture shapes without waiting for live services.
- [ ] Team 3 confirms the approved-candidate payload can create or update its source record.
- [ ] Both people agree that no discovery result can be queued without approval.

## Person A — Discovery, approval, and enrichment

### A1 — Audit and stabilize discovery

- [ ] Verify the explicit URL path accepts only public HTTP(S) URLs.
- [ ] Verify username validation matches the frontend contract.
- [ ] Verify Sherlock returns claimed accounts only.
- [ ] Verify Maigret returns claimed accounts only.
- [ ] Verify WhatsMyName ignores unsupported or unsafe site definitions.
- [ ] Verify provider failures become warnings and `partial: true`.
- [ ] Verify candidates normalize and deduplicate across providers.
- [ ] Verify confidence is deterministic and provider evidence is retained.
- [ ] Verify fixture mode returns the same public response shape as live mode.

### A2 — Implement explicit candidate approval

- [ ] Add a candidate-approval request model using the frozen contract.
- [ ] Validate the selected candidate URL again at approval time.
- [ ] Validate that the approval username matches `candidateUsername` when present.
- [ ] Require a canonical Team 3 project ID.
- [ ] Preserve URL, platform, username, confidence, match reason, and provider evidence.
- [ ] Call the agreed Team 3 source-creation/promote boundary.
- [ ] Ensure the result is saved as selected/approved, not crawled.
- [ ] Ensure approval never queues a crawl.
- [ ] Handle duplicate approved URLs according to the frozen contract.
- [ ] Return a clear result for a missing project, invalid URL, or duplicate source.

### A3 — Provider test coverage

- [ ] Test provider unavailable behavior.
- [ ] Test timeout behavior for Sherlock and Maigret.
- [ ] Test malformed provider output.
- [ ] Test one provider failure while another provider succeeds.
- [ ] Test cross-provider deduplication and high-confidence promotion.
- [ ] Test WhatsMyName stale-cache fallback.
- [ ] Test approval with valid discovery fixture data.
- [ ] Test approval rejects mismatched username or unsafe URL.
- [ ] Test approval does not create a crawl job.

### A4 — Graph export boundary

- [ ] Verify Gephi CSV ZIP output contains stable nodes and edges.
- [ ] Verify GEXF is valid and opens in Gephi.

### A handoff package

- [ ] Discovery fixture: success, empty, partial failure, unsafe URL rejection.
- [ ] Approval fixture: success, duplicate, missing project, invalid source.
- [ ] API contract note with field names and status codes.
- [ ] Test results and known provider limitations.

## Person B — Instagram, privacy, and live verification

### B1 — Freeze the Instagram behavior

- [ ] Confirm the request shape: `{ "username": "example.user" }`.
- [ ] Confirm normalized response fields required by Team 1.
- [ ] Confirm which fields are allowed to be shown for public accounts.
- [ ] Decide whether private accounts return status-only data or a reduced profile.
- [ ] Confirm recent posts are restricted to caption-bearing public data.
- [ ] Confirm images remain URLs only and are not downloaded or analyzed.
- [ ] Confirm Apify errors map to stable client-readable error codes.

### B2 — Implement the private-profile policy

- [ ] Add the agreed private-profile behavior to the endpoint/service.
- [ ] Ensure private-profile content is not promoted into evidence unless policy explicitly allows it.
- [ ] Ensure a private profile cannot silently become a crawlable source.
- [ ] Return an explicit status the frontend can render.
- [ ] Document the policy in the API contract and fixture descriptions.

### B3 — Harden the Apify adapter

- [ ] Confirm `APIFY_API_TOKEN` is documented in `.env.example` and local setup.
- [ ] Confirm the configured actor and request payload are current.
- [ ] Handle missing token with a stable `503` response.
- [ ] Handle profile not found with `404`.
- [ ] Handle rate-limit and service failures with retryable/unavailable status.
- [ ] Validate response shape before mapping fields.
- [ ] Limit recent posts to the agreed maximum.
- [ ] Ensure response fields remain optional when Apify omits them.

### B4 — Instagram tests and fixtures

- [ ] Add public-profile success fixture.
- [ ] Add private-profile fixture.
- [ ] Add profile-not-found fixture.
- [ ] Add missing-token fixture/response test.
- [ ] Add rate-limit/service-failure response test.
- [ ] Add invalid-username test.
- [ ] Add malformed upstream response test.
- [ ] Add test proving image URLs are returned but never downloaded.
- [ ] Add test proving private-profile policy is enforced.

### B5 — Live verification

- [ ] Use an approved public demo account only.
- [ ] Verify one successful Apify result with valid credentials.
- [ ] Verify no credentials are logged.
- [ ] Record API response fields actually returned by the actor.
- [ ] Confirm fixture data remains a safe fallback when Apify is unavailable.
- [ ] Record the date, actor version, and known limitations.

### B handoff package

- [ ] Instagram fixture set: public, private, not found, unavailable.
- [ ] API contract note with response and error fields.
- [ ] Private-profile policy note.
- [ ] Live verification note and configuration requirements.

## Joint integration sequence

### 1. Fixtures first

- [ ] A supplies discovery and approval fixtures.
- [ ] B supplies Instagram fixtures.
- [ ] Team 1 renders each fixture state.
- [ ] Team 3 validates the approved-candidate fixture against its source creation boundary.

### 2. Approval-to-source integration

- [ ] A and Team 3 connect approved candidates to the canonical source database.
- [ ] B verifies Instagram-derived public profile URLs follow the same approval rule.
- [ ] Confirm no action automatically queues a crawl.
- [ ] Confirm rejected and private-only results cannot be crawled.

### 3. End-to-end verification

- [ ] Search a prepared username in fixture mode.
- [ ] View discovery candidates and/or Instagram data.
- [ ] Explicitly approve one public source.
- [ ] Confirm Team 3 receives one canonical source record.
- [ ] Confirm Team 3 can queue the source only after approval.
- [ ] Confirm the frontend receives readable success and failure states.

## Definition of Team 2 done

- [ ] Discovery is safe, deterministic in fixture mode, and resilient to provider failures.
- [ ] Instagram behavior and private-account policy are explicit and tested.
- [ ] A user-approved public candidate has a documented, working handoff into Team 3's canonical source workflow.
- [ ] No discovery, Instagram, or enrichment result can trigger crawling automatically.
- [ ] Team 1 has all fixtures and contracts needed to connect the existing frontend.
- [ ] Team 3 has the approved-candidate payload and provenance needed to protect its crawl allowlist.
