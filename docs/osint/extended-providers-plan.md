# Extended OSINT Providers and Gephi Export Plan

## Objective

Extend the existing candidate-source discovery service with:

1. **Maigret** as an always-run broad username-discovery provider.
2. **WhatsMyName** as an always-run independent username cross-check provider.
3. **SpiderFoot** as a tightly scoped selected-source enrichment service.
4. **Gephi export** as an offline visualization output, not an application runtime dependency.

The existing manual URL, fixture, and Sherlock paths remain functional. Username queries run Sherlock, Maigret, and WhatsMyName together. New providers must return candidate public URLs through the existing `ProviderRecord` interface and must not crawl candidate content, write to SQLite, contact accounts, or automatically approve identity matches.

## Recommended implementation order

```text
Phase 1: Maigret provider
Phase 2: WhatsMyName provider and cross-provider confidence
Phase 3: Gephi CSV export
Phase 4: SpiderFoot sidecar and bounded enrichment
```

Do not begin SpiderFoot until Maigret, WhatsMyName, and the existing discovery tests are stable. SpiderFoot has a much larger operational and data surface than the other additions.

## Shared public API changes

Extend `ProviderName`:

```python
ProviderName = Literal[
    "sherlock",
    "maigret",
    "whatsmyname",
    "explicit_url",
]
```

Example multi-provider request:

```json
{
  "query": "demo-user",
  "queryType": "username",
  "limit": 25
}
```

The response shape remains unchanged:

```json
{
  "query": "demo-user",
  "candidates": [],
  "providersUsed": ["sherlock", "maigret", "whatsmyname"],
  "partial": false,
  "warnings": []
}
```

Provider failures remain non-fatal. If Maigret fails and Sherlock succeeds, return Sherlock candidates with `partial: true` and a typed warning.

## Dependency changes

Install discovery and graph dependencies as normal runtime requirements:

```toml
[project]
dependencies = [
  "sherlock-project>=0.16,<0.17",
  "maigret>=0.5,<0.6",
  "httpx>=0.27,<1",
]
  "networkx>=2.8,<3",
]
```

SpiderFoot runs as a separate service/container and is not installed inside the FastAPI environment.

## Proposed files

```text
apps/api/services/discovery/providers/
├── maigret.py
└── whatsmyname.py

apps/api/services/enrichment/
├── __init__.py
├── models.py
├── service.py
└── spiderfoot.py

apps/api/services/graph/
├── __init__.py
├── models.py
└── gephi.py

apps/api/routes/
├── enrichment.py
└── graph.py

apps/api/tests/
├── test_maigret_provider.py
├── test_whatsmyname_provider.py
├── test_spiderfoot_adapter.py
└── test_gephi_export.py

data/fixtures/
├── maigret-results.json
├── whatsmyname-data.json
├── spiderfoot-results.json
└── graph-input.json

data/cache/
└── whatsmyname-data.json
```

`data/cache/` must be ignored by Git. Deterministic fixtures remain committed.

---

# 1. Maigret Provider

## Purpose

Maigret checks a username across a larger site catalog and can return public profile URLs and linked identifiers. In this application, use only its public profile URL results. Do not import its dossier, profiling, or recursive identity conclusions into the candidate contract.

## Provider behavior

Implement `MaigretProvider` using the existing `DiscoveryProvider` protocol:

```python
class MaigretProvider:
    name = "maigret"

    async def discover(self, query: str) -> ProviderResult:
        ...
```

Run Maigret as a subprocess with:

- an argument array, never `shell=True`;
- a temporary output directory;
- JSON output;
- a provider-level site limit or tag filter;
- a per-site timeout;
- a separate whole-process timeout;
- no recursive search during the MVP.

## Normalization

For each confirmed public account result:

```python
ProviderRecord(
    url=profile_url,
    platform=site_name,
    candidate_username=query,
    exact_username_match=query.casefold() in profile_url.casefold(),
    provider="maigret",
    match_reason="Maigret found a public profile for the supplied username.",
)
```

Pass records through the existing normalization, deduplication, platform mapping, and scoring pipeline.

## Configuration

```text
MAIGRET_SITE_TIMEOUT_SECONDS=10
MAIGRET_PROCESS_TIMEOUT_SECONDS=60
MAIGRET_MAX_SITES=500
MAIGRET_RECURSIVE=false
```

## Failure behavior

| Failure | Warning code | Behavior |
|---|---|---|
| Executable missing | `PROVIDER_UNAVAILABLE` | Continue with other providers |
| Process timeout | `PROVIDER_TIMEOUT` | Kill process; continue |
| Nonzero exit | `PROVIDER_FAILED` | Include short sanitized diagnostic |
| Missing/malformed JSON | `PROVIDER_INVALID_OUTPUT` | Return no Maigret records |
| Individual site error | none or provider warning | Preserve successful records |

## Tests

- [ ] Missing executable returns a typed provider error.
- [ ] Command uses an argument array and never a shell.
- [ ] Confirmed accounts become `ProviderRecord` values.
- [ ] Unclaimed, disabled, and malformed results are skipped.
- [ ] Process timeout terminates the child process.
- [ ] Output is normalized and deduplicated with Sherlock results.
- [ ] Matching Sherlock + Maigret results receive high confidence.

---

# 2. WhatsMyName Provider

## Purpose

WhatsMyName is best used as an independent, data-driven cross-check. Its site definitions describe how to test whether a username appears to exist at a public profile URL.

## Dataset management

Use the official WhatsMyName JSON dataset through a configured URL:

```text
WHATS_MY_NAME_DATA_URL=https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json
WHATS_MY_NAME_CACHE_TTL_SECONDS=86400
WHATS_MY_NAME_SITE_TIMEOUT_SECONDS=8
WHATS_MY_NAME_PROCESS_TIMEOUT_SECONDS=45
WHATS_MY_NAME_MAX_CONCURRENCY=20
```

Rules:

1. Load the local cache when it is present and younger than the TTL.
2. Refresh the cache from the configured HTTPS URL when stale.
3. Validate the top-level JSON shape and required site-definition fields.
4. If refresh fails, use a stale cache and return a warning.
5. If no cache exists, return `PROVIDER_UNAVAILABLE`.
6. Never execute instructions or code from the dataset.

## HTTP checking

Use a shared `httpx.AsyncClient` with:

- bounded concurrency;
- redirects enabled only within HTTP(S);
- a fixed user agent;
- per-request timeout;
- response-size limit;
- no cookies persisted between sites;
- no requests to localhost, private, loopback, link-local, reserved, or metadata IP ranges.

Interpolate only the validated username into each site URL template. A site is a candidate only when its expected status/content rule matches and its known missing-account rule does not match.

## Provider records

```python
ProviderRecord(
    url=public_profile_url,
    platform=site_name,
    candidate_username=query,
    exact_username_match=query.casefold() in public_profile_url.casefold(),
    provider="whatsmyname",
    match_reason="WhatsMyName matched the public profile pattern for the supplied username.",
)
```

## Tests

- [ ] Fresh cache avoids a network download.
- [ ] Stale cache refreshes successfully.
- [ ] Failed refresh falls back to stale data with a warning.
- [ ] Private/local dataset targets are rejected.
- [ ] Expected existence and missing-account rules are respected.
- [ ] Concurrency never exceeds the configured maximum.
- [ ] A partial site failure does not fail the provider.
- [ ] Matching WhatsMyName + another provider raises confidence.

---

# 3. Gephi Export

## Purpose

Gephi is an offline graph-analysis and visualization application. Do not embed or automate the Gephi desktop application. Export graph files that a teammate can open in Gephi.

## API

Add:

```text
POST /api/graph/export?format=csv
POST /api/graph/export?format=gexf
```

Input:

```json
{
  "query": "demo-user",
  "candidates": [
    {
      "url": "https://github.com/demo-user",
      "platform": "github",
      "candidateUsername": "demo-user",
      "confidence": "high",
      "matchReason": "Exact username match reported by independent providers."
    }
  ],
  "providerEvidence": {
    "https://github.com/demo-user": ["sherlock", "maigret"]
  }
}
```

CSV response is a ZIP containing:

```text
nodes.csv
edges.csv
```

`nodes.csv` columns:

```text
Id,Label,Type,Platform,URL,Confidence
```

`edges.csv` columns:

```text
Source,Target,Type,Label,Weight
```

Graph model:

```text
username node
  ├── discovered_by → provider node
  └── possible_profile → public URL node

provider node
  └── reported → public URL node
```

Weights:

- high confidence: `3`
- medium confidence: `2`
- low confidence: `1`

## Implementation

- Use Python `csv`, `io`, and `zipfile` for CSV export.
- Use NetworkX only for GEXF export.
- Generate stable node IDs from a SHA-256 hash of node type and canonical value.
- Escape spreadsheet cells that begin with `=`, `+`, `-`, or `@` to prevent formula injection.
- Return downloads in memory; do not write user graph exports into the repository.

## Tests

- [ ] CSV ZIP contains both files.
- [ ] Node and edge headers match the contract.
- [ ] Duplicate candidates create one URL node.
- [ ] Provider evidence creates the correct edges.
- [ ] Confidence maps to the documented weights.
- [ ] Node IDs are stable across runs.
- [ ] Formula-like values are escaped.
- [ ] GEXF opens as valid XML and contains the same graph.

---

# 4. SpiderFoot Enrichment

## Purpose

SpiderFoot is a broad OSINT correlation platform. It does not fit the small `CandidateSource` provider contract. Run it as a separate local sidecar and expose a bounded enrichment endpoint only after a user has selected a public source.

## Deployment boundary

```text
FastAPI
  └── bounded SpiderFoot client
          └── SpiderFoot sidecar/container
```

Do not import SpiderFoot internals into the FastAPI process. Communicate through its supported HTTP/API boundary.

## API

Add:

```text
POST /api/enrichment/spiderfoot
GET  /api/enrichment/spiderfoot/{job_id}
```

Start request:

```json
{
  "target": "https://example.com/public-profile",
  "targetType": "url",
  "modules": ["account_finder", "web_content", "metadata"]
}
```

Start response:

```json
{
  "jobId": "sf_...",
  "status": "queued",
  "modules": ["account_finder", "web_content", "metadata"]
}
```

Only allow target types needed by the project:

- explicit public URL;
- public username;
- public domain.

## Module policy

Maintain a server-side allowlist. Client input can select only from the allowlist.

Allowed categories:

- public account discovery;
- public webpage/content analysis;
- public document/image metadata;
- public domain relationships needed for source provenance.

Always disabled:

- breach or leaked-credential searches;
- phone-number enrichment;
- private contact-data enrichment;
- dark-web/Tor searches;
- port scanning or banner grabbing;
- precise geolocation;
- bucket enumeration;
- cryptocurrency tracing;
- active exploitation or takeover checks.

Do not trust client-supplied SpiderFoot module names, target types, callbacks, or server URLs.

## Configuration

```text
SPIDERFOOT_ENABLED=false
SPIDERFOOT_BASE_URL=http://127.0.0.1:5001
SPIDERFOOT_API_TOKEN=
SPIDERFOOT_JOB_TIMEOUT_SECONDS=120
SPIDERFOOT_MAX_RESULTS=250
```

Default to disabled. The API returns `503` with a readable message until explicitly enabled.

## Result contract

Normalize accepted SpiderFoot results into:

```json
{
  "jobId": "sf_...",
  "status": "complete",
  "target": "https://example.com/public-profile",
  "findings": [
    {
      "type": "public_url",
      "value": "https://example.com/related-page",
      "source": "spiderfoot",
      "module": "web_content",
      "confidence": "medium"
    }
  ],
  "warnings": []
}
```

SpiderFoot findings are enrichment evidence, not automatically approved candidates. A user must select any new URL before it enters Firecrawl.

## Tests

- [ ] Disabled integration returns `503` without contacting a sidecar.
- [ ] Non-allowlisted target types and modules return `422`.
- [ ] Private/local URL targets are rejected except the configured sidecar URL.
- [ ] Sidecar authentication is sent only to the configured host.
- [ ] Timeouts and failed jobs return readable states.
- [ ] Result counts are capped.
- [ ] Disallowed result types are discarded.
- [ ] New URLs require user selection before crawling.

---

# Cross-provider scoring changes

The current deduplication infrastructure already merges identical canonical URLs. Extend evidence tracking so each aggregate retains its provider names.

Scoring rules:

| Evidence | Confidence |
|---|---|
| Explicit URL supplied by user | high |
| Same exact URL from two or more independent providers | high |
| Exact username in URL from one provider | medium |
| Fuzzy/pattern-only result from one provider | low |
| SpiderFoot-only related URL | low until user selection |

Do not treat several providers as independent when they consume the same underlying dataset. Record provider provenance so this can be audited.

# Frontend changes

Update the OSINT test UI after backend providers are stable:

- Add provider checkboxes for Sherlock, Maigret, and WhatsMyName.
- Show provider evidence on each candidate.
- Show partial-provider warnings without hiding successful results.
- Add “Export graph” for CSV/GEXF.
- Keep SpiderFoot behind a separate “Enrich selected source” action.
- Never run SpiderFoot automatically after discovery.

# Environment variables

Add to `.env.example`:

```text
MAIGRET_SITE_TIMEOUT_SECONDS=10
MAIGRET_PROCESS_TIMEOUT_SECONDS=60
MAIGRET_MAX_SITES=500
MAIGRET_RECURSIVE=false
WHATS_MY_NAME_DATA_URL=https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json
WHATS_MY_NAME_CACHE_TTL_SECONDS=86400
WHATS_MY_NAME_SITE_TIMEOUT_SECONDS=8
WHATS_MY_NAME_PROCESS_TIMEOUT_SECONDS=45
WHATS_MY_NAME_MAX_CONCURRENCY=20
SPIDERFOOT_ENABLED=false
SPIDERFOOT_BASE_URL=http://127.0.0.1:5001
SPIDERFOOT_API_TOKEN=
SPIDERFOOT_JOB_TIMEOUT_SECONDS=120
SPIDERFOOT_MAX_RESULTS=250
```

# Delivery phases

## Phase 1 — Maigret

- [x] Add runtime dependency and configuration.
- [ ] Add provider adapter and fixture.
- [ ] Register `maigret` in request validation and service construction.
- [ ] Add subprocess, parser, timeout, and deduplication tests.
- [ ] Verify Sherlock-only behavior is unchanged.

## Phase 2 — WhatsMyName

- [ ] Add dataset cache and validation.
- [ ] Implement bounded asynchronous checks.
- [ ] Register `whatsmyname` provider.
- [ ] Add cross-provider evidence and confidence tests.
- [ ] Verify stale-cache and partial-failure behavior.

## Phase 3 — Gephi export

- [ ] Add graph input/output models.
- [ ] Implement CSV ZIP export.
- [x] Add GEXF export.
- [ ] Add export action to the test UI.
- [ ] Test files manually in Gephi.

## Phase 4 — SpiderFoot

- [ ] Choose and document the exact sidecar version.
- [ ] Define the module allowlist from that version's module IDs.
- [ ] Add disabled-by-default configuration.
- [ ] Add start/status adapters and fixtures.
- [ ] Normalize and filter results.
- [ ] Add explicit user-selection handoff.

# Final acceptance criteria

- [ ] Existing fixture, explicit URL, and Sherlock tests still pass.
- [ ] Maigret and WhatsMyName can run independently.
- [ ] A duplicate URL reported by multiple independent providers appears once with high confidence.
- [ ] One failed provider produces warnings while preserving other results.
- [ ] Gephi exports contain stable, deduplicated nodes and edges.
- [x] SpiderFoot runs only on explicitly selected sources and cannot run a non-allowlisted module.
- [ ] No provider automatically triggers Firecrawl.
- [ ] All live providers can be replaced with fixtures for the demo.

# References

- Maigret: <https://github.com/soxoj/maigret>
- WhatsMyName: <https://github.com/WebBreacher/WhatsMyName>
- SpiderFoot: <https://github.com/smicallef/spiderfoot>
- Gephi: <https://gephi.org/>
