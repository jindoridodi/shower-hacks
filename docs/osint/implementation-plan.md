# OSINT Implementation Plan

## Objective

Build a small discovery service that accepts a username or explicit public URL and returns ranked candidate public sources in the canonical `CandidateSource[]` format.

OSINT is an optional discovery layer. It does not crawl pages, write to SQLite, generate reports, or contact anyone. The backend presents candidates for selection; only selected URLs move to the Firecrawl pipeline.

## Definition of done

- A username returns normalized, deduplicated candidate URLs.
- An explicit URL is validated and returned as a high-confidence candidate.
- Every result includes platform, confidence, and a human-readable match reason.
- Empty results and tool failures return valid empty responses, not server errors.
- The adapter works from a fixture when external tools are unavailable.
- Output matches the contract in `docs/06-team-integration-playbook.md`.

## Canonical contract

```ts
type CandidateSource = {
  url: string;
  platform: string;
  candidateUsername?: string;
  confidence: "high" | "medium" | "low";
  matchReason: string;
};
```

Recommended backend request:

```json
{
  "query": "example_username",
  "queryType": "username",
  "providers": ["sherlock"],
  "limit": 25
}
```

Recommended response:

```json
{
  "query": "example_username",
  "candidates": [
    {
      "url": "https://example.com/example_username",
      "platform": "example",
      "candidateUsername": "example_username",
      "confidence": "medium",
      "matchReason": "The public profile URL contains the exact supplied username."
    }
  ],
  "providersUsed": ["sherlock"],
  "partial": false,
  "warnings": []
}
```

The wrapper response is owned by the backend. The OSINT adapter owns only the `candidates` array.

## MVP architecture

```text
username or URL
      |
      v
input validation
      |
      +-------------------+
      |                   |
 explicit URL          username
      |                   |
 URL candidate      Sherlock adapter
      |                   |
      +---------+---------+
                |
                v
        normalize candidates
                |
                v
       deduplicate and score
                |
                v
       CandidateSource[] JSON
                |
                v
  backend selection -> Firecrawl
```

## Proposed file layout

The repository currently has documentation only. The OSINT owner should create the following files without changing backend, database, or Firecrawl contracts:

```text
apps/api/
├── services/
│   └── discovery/
│       ├── __init__.py
│       ├── service.py          # Orchestrates providers
│       ├── models.py           # CandidateSource and internal records
│       ├── normalize.py        # URL/platform normalization
│       ├── scoring.py          # Confidence rules
│       └── providers/
│           ├── __init__.py
│           ├── base.py         # Provider protocol
│           ├── explicit_url.py
│           ├── sherlock.py
│           └── fixture.py
├── routes/
│   └── discovery.py            # Thin HTTP route, owned with backend
└── tests/
    ├── test_discovery_service.py
    ├── test_normalize.py
    ├── test_scoring.py
    └── test_sherlock_provider.py

data/fixtures/
└── candidates.json
```

If the backend owner chooses a different package layout, preserve the same module boundaries and contract.

## Provider priority

### Phase 1: required

1. **Explicit URL provider** — validates a supplied `http` or `https` URL and emits one candidate.
2. **Fixture provider** — returns deterministic demo candidates.
3. **Sherlock provider** — runs username discovery and converts successful results into candidates.

### Phase 2: useful after the MVP works

4. **Maigret provider** — optional broader username coverage; use as a replacement or second provider, not a hard dependency.
5. **WhatsMyName cross-check** — optional second signal used to raise or lower confidence.
6. **Namechk** — optional lightweight presence check.

### Defer until after the demo

- Maltego transforms
- Gephi exports
- Wayback Machine and Common Crawl discovery
- Image and document metadata enrichment

These can enrich a later version but are not needed for the candidate-URL handoff.

## Input validation

### Username input

- Trim surrounding whitespace.
- Reject empty values.
- Set a conservative maximum length.
- Permit common username characters: letters, numbers, `_`, `-`, and `.`.
- Pass the username to subprocesses as an argument list, never through a shell string.
- Apply a provider timeout.

### URL input

- Accept only `http` and `https`.
- Normalize scheme and hostname casing.
- Remove URL fragments.
- Remove default ports.
- Preserve meaningful query parameters but remove known tracking parameters.
- Reject URLs containing embedded credentials.
- Do not follow URLs into private or loopback network ranges.

## Provider interface

```python
from typing import Protocol

class DiscoveryProvider(Protocol):
    name: str

    async def discover(self, query: str) -> list[dict]:
        """Return provider records; raise a typed provider error on failure."""
```

Provider records are internal. `service.py` converts them into `CandidateSource` objects so tool-specific fields never leak into the public contract.

## Sherlock adapter

### Responsibilities

- Execute Sherlock with a fixed timeout.
- Request a machine-readable result format.
- Parse only successful public-profile results.
- Convert each result to a provider record containing URL, platform, and username.
- Return partial results if some sites fail.

### Failure behavior

- Sherlock missing: return `PROVIDER_UNAVAILABLE` and allow fixture/manual URL fallback.
- Timeout: return partial results plus a warning.
- Invalid output: log a short diagnostic and return an empty provider result.
- Individual platform failure: skip that platform without failing the entire request.

Do not scrape profile contents inside this adapter. Firecrawl owns page retrieval.

## Normalization and deduplication

Normalize every candidate before scoring:

1. Lowercase the hostname.
2. Remove fragments.
3. Remove trailing slash except at the domain root.
4. Remove common tracking parameters.
5. Normalize known mobile or alternate platform hostnames when unambiguous.
6. Compute a canonical comparison key from hostname, path, and meaningful query parameters.

Deduplicate candidates by canonical comparison key. If multiple providers return the same URL:

- keep one candidate;
- retain the strongest confidence;
- combine provider evidence into one concise `matchReason`;
- preserve deterministic ordering.

## Confidence scoring

Confidence represents identity-match evidence, not whether the webpage is true.

### High

- The user supplied the exact URL directly; or
- two independent discovery providers find the same profile and the exact username appears in the canonical URL; or
- a candidate is linked from another already validated first-party source.

### Medium

- one provider finds a public profile whose canonical URL contains the exact username; or
- one strong first-party signal supports the match.

### Low

- the username is only a fuzzy match;
- the platform rewrites the handle and no corroborating signal exists; or
- the result is a search suggestion rather than a verified public profile.

Never promote a result solely because several weak results repeat the same unsupported assumption.

## Platform labeling

Prefer a stable lowercase platform identifier derived from a known hostname map:

```text
github.com      -> github
linkedin.com    -> linkedin
instagram.com   -> instagram
tiktok.com      -> tiktok
youtube.com     -> youtube
medium.com      -> medium
substack.com    -> substack
```

Use the registered hostname for unknown platforms. Do not derive platform labels from page titles.

## Fixture-first implementation

Create `data/fixtures/candidates.json` before integrating Sherlock:

```json
[
  {
    "url": "https://example.com/demo-user",
    "platform": "example",
    "candidateUsername": "demo-user",
    "confidence": "medium",
    "matchReason": "Fixture candidate with an exact username in the public URL."
  }
]
```

Fixture rules:

- Match the canonical contract exactly.
- Contain at least one candidate and one empty-result scenario.
- Never include secrets or a real private person’s data.
- Keep output deterministic for frontend development.

## Backend handoff

The backend should expose a discovery route such as:

```text
POST /api/discovery
```

The route should:

1. Validate the request.
2. Call the discovery service.
3. Return candidates without crawling them.
4. Let the user select candidates.
5. Pass selected URLs to the existing source/crawl endpoints.

The OSINT owner should coordinate the final route name with the backend owner because `POST /api/discovery` is not yet part of the frozen integration contract.

## Logging and observability

Log:

- request ID;
- provider name;
- query type, but avoid unnecessary raw personal data in logs;
- duration;
- candidate count;
- timeout or failure code.

Do not log full scraped content, API keys, subprocess environment variables, or sensitive source material.

## Test plan

### Unit tests

- [ ] Explicit URL produces one high-confidence candidate.
- [ ] Invalid schemes are rejected.
- [ ] URL credentials are rejected.
- [ ] Tracking parameters are removed.
- [ ] Duplicate URLs collapse into one candidate.
- [ ] Exact username match scores medium with one provider.
- [ ] Two independent exact matches score high.
- [ ] Empty provider results return `[]`.
- [ ] Provider timeout returns a warning, not a crash.
- [ ] Malformed provider output is ignored safely.

### Contract tests

- [ ] Every candidate has `url`, `platform`, `confidence`, and `matchReason`.
- [ ] `confidence` is only `high`, `medium`, or `low`.
- [ ] Optional `candidateUsername` is omitted rather than set to an invalid value.
- [ ] Fixture output matches live output shape.

### Integration test

```text
username
  -> fixture or Sherlock provider
  -> normalized CandidateSource[]
  -> backend response
  -> user selects one URL
  -> Firecrawl receives only that selected URL
```

## Implementation phases

### Phase 0 — 15 minutes: contract and fixture

- [ ] Confirm route name with backend owner.
- [ ] Add `CandidateSource` model.
- [ ] Add `candidates.json` fixture.
- [ ] Hand fixture to frontend and backend owners.

### Phase 1 — 30 minutes: deterministic core

- [ ] Implement explicit URL provider.
- [ ] Implement URL normalization.
- [ ] Implement deduplication.
- [ ] Implement confidence scoring.
- [ ] Add unit tests.

### Phase 2 — 45 minutes: Sherlock

- [ ] Implement subprocess adapter without shell execution.
- [ ] Add timeout and typed errors.
- [ ] Parse machine-readable output.
- [ ] Convert results to canonical candidates.
- [ ] Test with one prepared demo username.

### Phase 3 — 30 minutes: backend integration

- [ ] Connect the route to the service.
- [ ] Return warnings and partial state.
- [ ] Confirm no candidate is crawled automatically.
- [ ] Verify selected URLs reach the Firecrawl endpoint.

### Phase 4 — 30 minutes: failure and demo hardening

- [ ] Test missing Sherlock binary.
- [ ] Test timeout.
- [ ] Test zero results.
- [ ] Confirm fixture-mode toggle.
- [ ] Record one known-good demo query.

Stop after Phase 4 unless the end-to-end demo is already stable. Maigret and additional cross-check providers are stretch goals.

## Git and ownership plan

- Branch: `feat/osint`
- OSINT owner changes only discovery modules, OSINT tests, and the candidate fixture.
- Backend owner wires the final HTTP route or reviews the route commit.
- Integrator approves any contract change.
- Commit the fixture first, then the deterministic core, then the Sherlock adapter.

Suggested commits:

```text
Add OSINT candidate fixture and models
Implement URL discovery normalization and scoring
Add Sherlock discovery adapter
Connect OSINT discovery route
Add OSINT failure handling and tests
```

## Handoff checklist

- [ ] Branch name shared with integrator.
- [ ] Candidate fixture committed.
- [ ] Contract tests passing.
- [ ] One live provider tested.
- [ ] Empty and failure states tested.
- [ ] Usage note added.
- [ ] Known limitations documented.
- [ ] Ready-for-integration message posted using the team template.

## Stretch goals

Only attempt these after the fixture-only and live Sherlock paths both work:

- Add Maigret as an optional provider.
- Cross-check candidates with WhatsMyName.
- Export a simple candidate relationship graph.
- Add archival-source suggestions for already selected URLs.
- Add provider metrics to the demo diagnostics panel.
