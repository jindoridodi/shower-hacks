# Factual Generation

## Prompt contract

The model receives the task type, retrieved excerpts, source IDs, and confidence rules. It must say “unknown” when evidence is insufficient.

The model returns structured claims with `text`, `claim_type`, `confidence`, and `source_ids`.

## Validation

- [ ] Every claim has a source ID.
- [ ] Every source ID exists in SQLite.
- [ ] Quotes match source text.
- [ ] Unsupported facts are removed.
- [ ] Inferences are labeled.
