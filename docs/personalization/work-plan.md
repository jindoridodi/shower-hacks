# Personalization Work Split

## Purpose

Owner A and Owner B work in separate branches and do not edit each other’s owned files. The canonical cross-team interfaces remain in `docs/06-team-integration-playbook.md`.

## Branches

| Owner | Branch | Scope |
|---|---|---|
| Owner A | `feat/personalization-generation` | Evidence-backed generation, validation, prompts, and fixtures |
| Owner B | `feat/personalization-ui` | Timeline and communication-draft review UI |

## Contract rules

- Use the playbook’s canonical JSON names: `sourceId`, `sourceIds`, `claimType`, and `reviewRequired`.
- Do not rename API fields or change SQLite tables.
- Propose contract changes in `docs/operations/decisions.md` and notify the integrator before implementation.
- The frontend consumes fixture JSON or backend responses; it never reads SQLite or calls generation services directly.

## Owner A — Personalization generation

### Owns

- `apps/api/services/`
- `packages/prompts/`
- `data/fixtures/evidence-excerpts.json`
- `data/fixtures/report.json`
- `data/fixtures/timeline.json`
- `data/fixtures/communication-draft.json`
- Personalization-focused tests under `tests/`

### Builds

1. Evidence retrieval input handling for safe `EvidenceExcerpt` records.
2. Structured `Report` generation with cited claims, contradictions, and unknowns.
3. Claim validation that rejects missing or invalid source IDs, unsupported quotes, invalid confidence, and observed claims using inference language.
4. Prompt contracts for factual profiles, uncertainty reports, and communication drafts.
5. Review-only `CommunicationDraft` generation with the exact AI-generated label and `reviewRequired: true`.
6. Timeline extraction that returns only explicitly published dates and source-linked events.
7. Fixture data and tests for valid evidence, empty evidence, invalid citations, and unsupported claims.

### Must not build

- React screens, browser state, or evidence-drawer UI.
- Calendar-provider integrations.
- Message sending, posting, emailing, target impersonation, or voice imitation.

### Handoff to Owner B

Provide the fixture paths, exact response shapes, an empty-evidence example, and a known-limitation note.

## Owner B — Personalization UI

### Owns

- Personalization-related components and pages under `apps/web/`.
- UI tests for those components.

### Builds

1. A chronological `Timeline` that renders `TimelineItem` fixture/API data.
2. A `DraftReview` view with the AI-generated label, editable fields, source panel, and visible review-required state.
3. Report rendering that distinguishes observed, inferred, uncertain, and unknown material.
4. Source links or an evidence drawer driven by `sourceIds`.
5. Loading, empty, error, and fixture-fallback states.

### Must not build

- Generation prompts, LLM calls, claim validation, or retrieval logic.
- Changes to Owner A fixtures or API field names.
- Automatic sending, posting, or calendar-provider integrations.

### Handoff to Owner A and the integrator

Report any missing UI data as a proposed optional contract addition. Do not add fields locally.

## Integration sequence

1. Owner A commits fixture JSON first.
2. Owner B builds against those fixtures without waiting for a live API.
3. Owner A connects generation to safe evidence retrieval.
4. Owner B swaps fixture loading for the backend response one endpoint at a time.
5. The integrator merges working slices and verifies the fixture-only demo still works.

## Ready-to-merge checks

### Owner A

- [ ] Fixtures match the canonical interfaces.
- [ ] Every returned factual claim has valid source IDs.
- [ ] Empty evidence returns no factual claims.
- [ ] Drafts are labeled and review-only.
- [ ] Focused tests pass.

### Owner B

- [ ] Timeline and draft review render fixture data.
- [ ] Claim types, confidence, and source links are visible.
- [ ] Loading, empty, and error states work.
- [ ] No UI path sends a message or impersonates the subject.
