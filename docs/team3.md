# Team 3 Two-Person Implementation Plan

## Goal

Deliver a safe, demonstrable backend path from an explicitly approved public
source to an attributable, evidence-backed report:

```text
project → source approval → queued crawl → stored document → safe excerpts
→ cited report/draft → frontend-readable API responses
```

This plan divides Team 3's work into two independent ownership areas. Both
people work against fixtures until the adjacent live dependency is ready.

## Existing gaps to close first

- The documented `/api/...` contract and the implemented root-level routes
  (`/projects`, `/sources`, `/crawls`) disagree.
- `Source` has no approval or allowlist fields, so a source can currently be
  queued without explicit approval.
- `workers/crawl_worker.py`, `workers/report_worker.py`, and
  `workers/embedding_worker.py` are empty.
- Generated report and draft endpoints accept browser-provided excerpts and
  currently do not use `project_id` to retrieve server-side evidence.
- The frontend needs fixture shapes and stable route names before it can safely
  replace the prototype data.

## Ownership

| Owner | Owns | Does not own |
| --- | --- | --- |
| Person A — Source and crawl platform | API contract, projects/sources, explicit approval and allowlist enforcement, URL policy, crawl jobs, worker execution, Firecrawl adapter, crawl health | Report-generation logic, prompt behavior, frontend screens |
| Person B — Evidence, reports, and delivery | Document processing, sensitivity gating, retrieval, server-side report/draft orchestration, claims/citations, operational documentation, full test and demo readiness | Source approval semantics, crawl queue behavior, Firecrawl transport |

Person A is the final owner of public-source eligibility. Person B is the final
owner of whether stored content is eligible to enter a generation prompt.

## Shared decisions to lock on day 1

Person A writes these decisions in `docs/04-integration-contract.md`; Person B
reviews them before implementation starts.

1. Use one canonical external route convention. Adopt `/api/...` routes for
   frontend-facing endpoints and either remove or temporarily preserve root
   routes as documented compatibility aliases.
2. Use crawl states `pending`, `queued`, `running`, `succeeded`, and `failed`.
   Do not introduce `complete` or `partial` as persisted status values; represent
   partial retrieval through result/error metadata if it is needed.
3. A source is crawlable only when all are true: it is a valid public HTTP(S)
   URL, it belongs to the selected project, it has explicit approval, and it is
   in that project's crawl allowlist.
4. Reports and drafts retrieve eligible excerpts on the server from the given
   project. The browser may request a report mode, but it cannot supply
   untrusted evidence as the generation corpus.
5. Fixture-mode responses have exactly the same JSON shape as live responses.

## Workstream A — Source and crawl platform

### A1. Freeze the API and schema contract

- Define request, response, error, and fixture shapes for projects, sources,
  approvals, crawls, documents, reports, and drafts.
- Add a `GET /api/projects` list endpoint and settle the nested project/source
  route shape used by the frontend.
- Create a migration and model/schema updates for source approval state,
  approval timestamps, source provenance, and crawl-allowlist membership.
- Preserve canonical URL uniqueness within a project.

**Acceptance check:** a frontend developer can create/list a project, create a
source, inspect its approval state, and see documented errors without reading
the database directly.

### A2. Enforce explicit approval and public-target policy

- Validate and canonicalize submitted URLs; reject credentials, loopback/local,
  private-network, malformed, and unsupported targets.
- Add approve, reject, and remove source actions. Record approval separately
  from discovery confidence.
- Reject crawl queue requests for pending, rejected, removed, or otherwise
  non-allowlisted sources.
- Ensure duplicate active crawl prevention remains transactional.
- Keep discovery, Instagram, and enrichment read-only: none may queue a crawl
  implicitly.

**Acceptance check:** tests prove an unapproved source returns a readable 4xx
error when queued, while an approved public source can be queued exactly once.

### A3. Implement crawl execution

- Implement `workers/crawl_worker.py` to claim queued jobs safely, call
  `run_queued_crawl`, and record terminal failures without leaking secrets or
  source content into logs.
- Complete the Firecrawl adapter's live and fixture behavior, including timeout,
  retry classification, redirect validation, terms/robots/rate-limit checks,
  and public-target boundaries.
- Persist crawl start/completion/failure metadata and create an attributable
  document on success.
- Add API/database/worker health checks and a clean worker startup path.

**Acceptance check:** an approved fixture URL reaches `succeeded` and creates a
document; an unavailable Firecrawl dependency reaches `failed` with a safe,
readable error.

### A4. Handoff to Person B

Provide:

- frozen OpenAPI-style route table and JSON examples;
- migrations plus seed/reset instructions;
- approved-source, queued-crawl, successful-crawl, and failed-crawl fixtures;
- an integration test proving the source-to-document path.

## Workstream B — Evidence, reports, and delivery

### B1. Make crawled documents usable evidence

- Complete document cleanup, chunking, content-hash deduplication, FTS records,
  and retrieval over successful project sources.
- Run sensitivity filtering before retrieval for generation. Mark blocked or
  redacted material in storage, and exclude it from prompt construction.
- Return attributable excerpts that include source ID, canonical URL, title,
  text, and sensitivity status.
- Return an empty evidence set and explicit unknowns when no safe support exists;
  never fabricate a citation.

**Acceptance check:** a seeded successful crawl produces retrievable excerpts;
sensitive content is stored with its status but never appears in the generation
input.

### B2. Make generation project-backed

- Change report and draft endpoints so `project_id` determines the retrieved
  evidence corpus.
- Connect report generation to safe excerpts, claim validation, citations,
  contradictions, uncertainty, unknowns, and timeline extraction.
- Persist report claims and claim-source links; reject unsupported claims or
  sources from another project.
- Keep drafts review-only and retain the AI-generated/review-required labels.
- Support deterministic fixture mode and readable missing-model/dependency
  errors.

**Acceptance check:** a project with safe documents returns a cited report whose
claim source IDs resolve to stored excerpts; a project without safe evidence
returns unknowns and no unsupported claims.

### B3. Test, operate, and document

- Add tests for documents, filtering, retrieval, report generation, claim
  validation, cross-project source rejection, drafts, and dependency failures.
- Complete local setup, environment-variable, deployment, fixture-only, and
  clean-restart instructions.
- Add a project license before public release.
- Produce a demo runbook that includes live and fixture fallback behavior.

**Acceptance check:** the complete Python suite passes from an empty database,
and the fixture-only demo can be rehearsed without any external API key.

### B4. Handoff to Person A and frontend integration

Provide:

- evidence, report, timeline, and draft fixtures;
- documented generation failure modes;
- an integration test for document-to-report behavior;
- a short frontend mapping for claims, excerpts, uncertainty, and draft labels.

## Execution sequence

| Checkpoint | Person A | Person B | Exit criteria |
| --- | --- | --- | --- |
| 0. Contract freeze | Drafts routes, statuses, approval model, fixtures | Reviews evidence/report fields | One documented contract and fixture set |
| 1. Parallel foundation | Migrates approval/allowlist and guards queueing | Completes fixture-backed document/retrieval path | Approval and safe-evidence unit tests pass |
| 2. First tracer slice | Implements worker and fixture crawl completion | Generates a cited fixture-backed report from stored excerpts | Approved source → document → report works locally |
| 3. Live dependency swap | Enables Firecrawl with safe failure behavior | Enables model-backed generation with safe failure behavior | Each swap keeps fixture mode functional |
| 4. Release gate | Verifies health, worker, and crawl failures | Runs full suite, clean restart, docs, and demo rehearsal | End-to-end test and fixture demo pass |

## Shared end-to-end test

Add one integration test jointly owned by both people:

```text
create project
  → create candidate/manual source
  → explicitly approve source
  → queue crawl
  → worker stores successful document
  → filter and retrieve safe excerpts
  → generate report
  → verify every returned claim links to stored evidence
```

Also test these negative paths: invalid/private URL, unapproved source, duplicate
active crawl, Firecrawl timeout, no safe evidence, unsupported claim, missing
model key, and clean fixture-only restart.

## Merge and coordination rules

- Person A changes source, crawl, URL-policy, worker, Firecrawl, and route
  contract files.
- Person B changes document-processing, retrieval, report/draft, operations,
  and corresponding test files.
- Neither person changes the other owner's response fields without first
  updating `docs/04-integration-contract.md` and providing a compatible fixture.
- Merge after each checkpoint, not as one large end-of-week integration branch.
- Keep external dependencies optional: fixture mode must remain runnable
  throughout implementation.
