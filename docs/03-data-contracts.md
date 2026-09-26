# Data Contracts

## Source

Corpus sources live in `sources`. A source has no `title` or `source_type` column. Page title is stored on `documents.title`. Status values are `pending`, `queued`, `running`, `succeeded`, and `failed`.

```json
{
  "id": "src_001",
  "project_id": "proj_001",
  "url": "https://example.com/page",
  "canonical_url": "https://example.com/page",
  "scraped_at": "2026-09-26T18:00:00.000000+00:00",
  "content_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "status": "succeeded"
}
```

## Document and chunk

`documents.raw_text` stores scraped HTML when a caller supplies it. Cleaned markdown is `documents.cleaned_text`. Ingest also writes that markdown to `data/raw/{source_id}/{hash}.md` and stores the repo-relative path in `documents.raw_path`.

`document_chunks.text` is the chunk body. `document_chunks.fts_text` copies that body for the shared chunk contract. Search still reads the FTS5 table `document_chunks_fts` through `GET /search/chunks`. `document_chunks.embedding` is present and nullable; this milestone does not generate or query embeddings.

Document sensitivity is `unreviewed`, `clear`, `sensitive`, or `redacted`. New scraped documents stay `unreviewed` until a later review marks them.

## Claim

Generation still speaks `text`, `claimType`, `confidence`, and `sourceIds`. The corpus stores `claim_text` and one `claim_sources` row per cited source. `confidence` is not stored. An unknown with no source id is stored as a claim with no citation rows.

```json
{
  "id": "claim_001",
  "report_id": "report_001",
  "claim_text": "The subject repeatedly describes hiking as a weekend activity.",
  "position": 0,
  "sources": [
    {"source_id": "src_001", "excerpt": "hiking as a weekend activity"}
  ]
}
```

## Claim types

- `observed`: directly supported by a source.
- `inferred`: supported by multiple signals and visibly labeled.
- `uncertain`: conflicting or incomplete evidence.
- `unknown`: the corpus does not establish the claim.

There is no `invented` claim type.
