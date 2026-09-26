# Data Contracts

## Source

```json
{
  "id": "src_001",
  "project_id": "proj_001",
  "url": "https://example.com/page",
  "title": "Example page",
  "source_type": "public_webpage",
  "scraped_at": "2026-09-26T18:00:00Z",
  "content_hash": "sha256:...",
  "status": "complete"
}
```

## Claim

```json
{
  "id": "claim_001",
  "report_id": "report_001",
  "text": "The subject repeatedly describes hiking as a weekend activity.",
  "claim_type": "observed",
  "confidence": 0.86,
  "source_ids": ["src_001", "src_004"],
  "status": "supported"
}
```

## Claim types

- `observed`: directly supported by a source.
- `inferred`: supported by multiple signals and visibly labeled.
- `uncertain`: conflicting or incomplete evidence.
- `unknown`: the corpus does not establish the claim.

There is no `invented` claim type.
