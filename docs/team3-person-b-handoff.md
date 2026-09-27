# Team 3 Person B — Evidence and Reports Handoff

## What this slice provides

Person B owns the boundary from stored documents to generation-safe,
source-attributable report output.

```text
clear document chunks → safe evidence excerpts → generated report/draft
→ validated source IDs → persisted claim-source excerpts
```

The implementation does not make a source crawlable, select Firecrawl targets,
or execute crawl jobs. Those remain Person A responsibilities.

## Safe evidence contract

`apps.api.services.evidence.list_safe_excerpts(db, project_id)` is the only
generation-facing retrieval seam.

It returns at most 50 excerpts by default, each shaped as:

```json
{
  "sourceId": "source-id",
  "sourceTitle": "Optional public page title",
  "sourceUrl": "https://example.com/public-page",
  "text": "Attributable document chunk text",
  "sensitivityStatus": "safe"
}
```

Only stored documents with `sensitivity_status == "clear"` are eligible.
`unreviewed`, `sensitive`, and `redacted` documents are excluded from model
input. The service returns an empty list when a project has no eligible evidence
and returns `project_not_found` for an unknown project.

## Report and draft behavior

The project generation routes now retrieve evidence server-side:

```text
POST /api/projects/{project_id}/reports
POST /api/projects/{project_id}/drafts
```

Browser-supplied `evidenceExcerpts` are ignored. A report request supplies a
report ID, mode, optional timestamp, and fixture flag; a draft request supplies
recipient and fixture flag. The requested project determines the evidence
corpus.

When no safe evidence exists:

- reports return no factual claims and an explicit unknown;
- drafts return an empty subject/body/source list while preserving the exact
  AI-generated label and `reviewRequired: true`.

Generated reports persist their claims and source excerpts through the existing
`reports`, `report_claims`, and `claim_sources` tables. A citation that does not
resolve to the retrieved project evidence is rejected before a report shell is
created. Because the current public claim contract supplies source IDs rather
than chunk IDs, persistence retains every retrieved chunk for each cited source
instead of selecting an arbitrary chunk. Timeline parsing preserves invalid
date-shaped strings as imprecise items rather than failing the report.

## Fixture and live mode

`useFixtures: true` selects deterministic report/draft fixture output after
safe project evidence retrieval. Fixture report source IDs must match the safe
source IDs returned for the fixture project; do not use fixture output as a way
to inject browser-controlled evidence.

`useFixtures: false` requires the configured text model. Missing or failed model
dependencies return a readable generation error. Fixture mode must remain
available while the model or Firecrawl is unavailable.

## Person A dependency

For the live vertical slice, Person A must provide an approved source that
reaches a terminal crawl state and stores filtered documents. The ingestion path
must supply clear document chunks; Person B will not promote an unreviewed or
redacted document to `safe` evidence.

## Verification

Run in a configured development environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m pytest tests/test_evidence.py tests/test_evidence_report_integration.py \
  tests/test_generation_routes.py tests/test_firecrawl_stub.py \
  tests/test_timeline_extractor.py
```

Person B acceptance path:

1. Create a project and an approved public source through Person A's contract.
2. Complete a prepared fixture crawl that creates a `clear` document and chunks.
3. Request a fixture-backed report for that project.
4. Confirm every returned claim source ID resolves to a stored excerpt.
5. Request a draft and confirm its AI label, source IDs, and review requirement.
6. Repeat with no safe evidence and confirm no factual claim or nonempty draft is
   produced.
7. Confirm malformed dates remain visible without a generation failure.

## Known limitations for integration

- Pytest is not installed in the current workspace, so pytest-fixture tests must
  run in the documented virtual environment.
- Person A still owns the approval/allowlist, worker, and Firecrawl completion
  path required for a live end-to-end demonstration.
- The canonical external route/status contract must be frozen by Person A before
  Team 1 binds its typed API client.
