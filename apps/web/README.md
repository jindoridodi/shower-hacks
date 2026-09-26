# Personalization UI

## Fixture mode

The personalization page is available at `/personalization`. It reads the canonical fixture files in `data/fixtures/` when `NEXT_PUBLIC_USE_FIXTURES` is unset or set to `true`.

```text
NEXT_PUBLIC_USE_FIXTURES=true
```

Set `NEXT_PUBLIC_USE_FIXTURES=false` only after a live personalization adapter is available. Until then, the page displays a readable loading error instead of substituting content.

## Manual acceptance checks

1. Open `/personalization` with fixture mode enabled.
2. Confirm report claims display a claim type, confidence, and evidence link.
3. Confirm the precisely dated timeline event is ordered chronologically and the year-only event appears in the imprecise-date section.
4. Confirm draft recipient, subject, and body are editable.
5. Confirm the exact AI-generated label and review-required notice are visible.
6. Select a source from any view and confirm its evidence excerpt appears.
7. Confirm there is no send, post, email, export, or calendar action.

The repository does not currently include a frontend package manifest or test runner. Add component tests only when the frontend runtime and test tooling are introduced.
