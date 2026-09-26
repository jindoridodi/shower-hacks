# Team Integration Playbook

This is the one file every engineer should read before starting work. Its purpose is to remove blocking dependencies: each team builds against stable contracts, fixtures, and fallback behavior—not another team’s unfinished code.

## Operating rule

**No team waits for another team to finish.** If an upstream dependency is not ready, use the fixture, mock response, or local interface described below. Replace the mock only when the real service is available.

## The system in one picture

```text
                 ┌──────────────────────┐
                 │      Frontend        │
                 │ input / progress /   │
                 │ report / sources     │
                 └──────────┬───────────┘
                            │ HTTP only
                            v
                 ┌──────────────────────┐
                 │       Backend        │
                 │ validate / orchestrate│
                 │ return stable JSON   │
                 └─┬─────────┬────────┬─┘
                   │         │        │
                   v         v        v
          ┌────────────┐ ┌────────┐ ┌──────────────┐
          │ Discovery  │ │Firecrawl│ │    SQLite     │
          │ optional   │ │ scrape  │ │ source of truth│
          └────────────┘ └────────┘ └──────┬───────┘
                                             │
                                             v
                                  ┌──────────────────┐
                                  │ Retrieval + LLM  │
                                  │ cited claims only│
                                  └──────────────────┘
```

## Ownership map

| Workstream | Owns | Must provide | Must not change without agreement |
|---|---|---|---|
| Frontend | Screens, components, browser state | UI that works against fixture JSON | API field names |
| Backend | Routes, validation, orchestration | Stable HTTP response shapes | SQLite tables owned by Database |
| OSINT | Optional public-URL suggestions | `CandidateSource[]` JSON fixture | Crawl behavior or report UI |
| Firecrawl | Crawl adapter and normalization | `CrawlResult` JSON fixture | Frontend behavior or DB schema |
| Database | SQLite schema, queries, reset/seed | Seed script and repository interface | API response shapes |
| Personalization | Retrieval, claim validation, prompts | `Report` and `Draft` JSON fixtures | Raw crawl logic or frontend state |
| Integrator | Main branch, fixtures, full demo | End-to-end test path | Feature ownership boundaries |

The owner is the only person who changes a workstream’s contract. Everyone else consumes it.

## Canonical interfaces

These interfaces are the boundary between teams. They are deliberately small. Add fields only as optional fields until the demo is stable.

### 1. Frontend ↔ Backend

The frontend **never** reads SQLite directly or calls Firecrawl directly. It calls the backend only.

```text
POST /api/projects
POST /api/projects/{project_id}/sources
POST /api/projects/{project_id}/crawls
GET  /api/crawls/{crawl_id}
GET  /api/projects/{project_id}/corpus
POST /api/projects/{project_id}/reports
POST /api/projects/{project_id}/drafts
GET  /api/health
```

Frontend can begin immediately by loading fixture responses from `data/fixtures/` that match these response shapes.

### 2. OSINT → Backend

OSINT returns candidate public URLs. It does not crawl, persist, or produce a report.

```ts
type CandidateSource = {
  url: string;
  platform: string;
  candidateUsername?: string;
  confidence: "high" | "medium" | "low";
  matchReason: string;
};
```

Backend behavior:

1. Validate URL format.
2. Return candidates to the frontend for selection.
3. Crawl only selected candidates.

Fallback: `data/fixtures/candidates.json`.

### 3. Firecrawl → Backend → Database

The Firecrawl adapter receives a selected public URL and returns normalized page data. It does not know anything about React screens, LLM prompts, or SQLite tables.

```ts
type CrawlResult = {
  url: string;
  canonicalUrl?: string;
  title?: string;
  markdown: string;
  links: string[];
  scrapedAt: string;
  status: "complete" | "partial" | "failed";
  error?: string;
};
```

Database behavior:

1. Store the source row.
2. Store normalized document content.
3. Store crawl status and error, if any.
4. Return source IDs to the backend.

Fallback: `data/fixtures/crawl-results.json`.

### 4. Database → Personalization

Personalization never owns raw crawl storage. It asks the database repository for eligible excerpts.

```ts
type EvidenceExcerpt = {
  sourceId: string;
  sourceTitle?: string;
  sourceUrl: string;
  text: string;
  sensitivityStatus: "safe" | "restricted";
};
```

Personalization only receives `safe` excerpts. It returns no claim when retrieval is empty.

Fallback: `data/fixtures/evidence-excerpts.json`.

### 5. Personalization → Backend → Frontend

Personalization returns structured output. It does not return an unstructured chat response.

```ts
type Claim = {
  id: string;
  text: string;
  claimType: "observed" | "inferred" | "uncertain" | "unknown";
  confidence: number;
  sourceIds: string[];
};

type Report = {
  id: string;
  title: string;
  claims: Claim[];
  contradictions: string[];
  unknowns: string[];
  generatedAt: string;
};
```

Frontend behavior:

- Render the claim type and confidence.
- Resolve `sourceIds` to source cards or an evidence drawer.
- Show unknowns rather than fabricating an answer.

Fallback: `data/fixtures/report.json`.

### 6. Timeline / calendar extraction

Timeline is a report subfeature, not a separate application or calendar integration.

```ts
type TimelineItem = {
  dateText: string;
  normalizedDate?: string;
  eventText: string;
  sourceId: string;
  confidence: number;
};
```

The frontend renders a chronological list. Do not block the MVP on Google Calendar, Outlook, or scheduling APIs.

### 7. Communication drafts

Drafts are source-linked and review-only. The application does not send messages, posts, or emails.

```ts
type CommunicationDraft = {
  label: "AI-generated draft — review before use";
  recipient: string;
  subject?: string;
  body: string;
  sourceIds: string[];
  reviewRequired: true;
};
```

## Fixture-first development

Create these files before integrating real services:

```text
data/fixtures/
├── candidates.json
├── crawl-results.json
├── evidence-excerpts.json
├── report.json
├── timeline.json
└── communication-draft.json
```

Rules:

- Each fixture must match the canonical interface exactly.
- Each workstream commits its fixture with its first commit.
- The frontend toggles `USE_FIXTURES=true` locally when the API is unavailable.
- The backend toggles fixture adapters when Firecrawl, discovery, or the LLM is unavailable.
- The end-to-end demo must work entirely from fixtures.

## Build order that prevents blockers

### Phase A — 20 minutes: contracts and fixtures

- [ ] Integrator creates the fixture directory.
- [ ] Each workstream adds its JSON fixture.
- [ ] Backend creates routes that return fixture shapes.
- [ ] Frontend renders fixture shapes.

At the end of this phase, the demo should be clickable even with no external APIs.

### Phase B — parallel implementation

| Team | Build independently against | Definition of done |
|---|---|---|
| Frontend | Fixture API responses | Every screen renders fixture data and error states |
| Backend | Endpoint contract + fixture adapters | All endpoints return contract-compliant JSON |
| OSINT | `CandidateSource` contract | Candidate fixture + working adapter |
| Firecrawl | `CrawlResult` contract | One URL returns normalized content or a clear error |
| Database | SQLite repository interface | Seed, insert, fetch, reset all work locally |
| Personalization | `EvidenceExcerpt` input + `Report` output | At least one cited report works from fixture excerpts |

### Phase C — integration swaps

Replace one fixture adapter at a time:

1. Database replaces in-memory source fixture.
2. Firecrawl replaces crawl fixture.
3. Personalization replaces report fixture.
4. OSINT replaces candidate fixture.

After every swap, run the existing demo path. If it breaks, restore the fixture adapter and fix in the owning branch.

## Git rules for a six-hour hackathon

```text
main
├── feat/frontend
├── feat/backend
├── feat/firecrawl
├── feat/database
├── feat/personalization
└── feat/osint
```

- One owner per branch.
- The integrator owns `main` and merges only working slices.
- Branches should touch their own directories whenever possible.
- Do not change another team’s contract file directly; write a proposed change in `docs/operations/decisions.md` and alert the integrator.
- Merge fixtures early, implementation later.
- Rebase/merge conflicts are the integrator’s job, not a reason for the team to stop working.
- After the final 90 minutes, merge bug fixes only.

## Definition of done for every feature

Before a feature reaches `main`, its owner confirms:

- [ ] It works using its own fixture.
- [ ] It handles an empty result.
- [ ] It returns a readable error.
- [ ] It does not change another contract unexpectedly.
- [ ] It includes one short usage note or test.
- [ ] It does not block the fixture-only demo.

## Integration handoff template

Paste this into the team chat when a slice is ready:

```text
Workstream: [frontend / backend / firecrawl / database / personalization / osint]
Branch: [branch name]
Provides: [endpoint, component, adapter, or query]
Consumes: [exact contract or fixture file]
Fixture tested: [yes/no]
Happy path tested: [yes/no]
Failure state tested: [yes/no]
Known limitation: [one sentence]
Ready for integration: [yes/no]
```

## Emergency fallback

If any service is not working during the final hour:

1. Flip that adapter to fixture mode.
2. Keep the same UI and demo narrative.
3. Do not attempt a last-minute rewrite of another team’s feature.
4. Preserve the source ledger and report reveal—the core artwork still works.
