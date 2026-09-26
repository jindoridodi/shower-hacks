# People search schema handoff

The future search implementation should map its results into JSON with these
top-level collections:

```json
{
  "searches": [{"name": "...", "prompt": "..."}],
  "sources": [],
  "documents": [],
  "document_chunks": [],
  "errors": [],
  "generated_at": "..."
}
```

Each successful result uses the shared records:

```text
Source: id, project_id, url, canonical_url, scraped_at, content_hash, status
Document: id, source_id, raw_path, cleaned_text, sensitivity_status
DocumentChunk: id, document_id, chunk_index, text, embedding, fts_text
```

The search and orchestration implementation will be reconnected after the other
branch is merged. The URL fixture in
[`documents/people-search-urls.json`](../../documents/people-search-urls.json)
contains the current candidates for the `emily thach` test.

When reconnected, discovered pages should use Firecrawl v2 JSON mode with an
embedded profile schema, a focused extraction prompt, and prompt-injection
checking. The extracted JSON should be serialized into `Document.cleaned_text`,
with original Markdown retained at `Document.raw_path`.

Candidate URLs that cannot be legally or technically scraped should remain
traceable as source records with an error status. A matching name is not proof of
identity.
