# Document processing handoff (Sehyun)

Python standard library only; no API keys, network, models or workers required.
English is the supported language for this pipeline: detection rules, examples,
status/error messages and search validation use English. There is no automatic
translation or language rejection. Unicode source text is preserved, but
non-English contextual sensitivity detection is unsupported.

Run from repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Emily: inspect BEFORE storing or logging

```python
from apps.api.services.sensitivity import prepare_for_storage

checked = prepare_for_storage(markdown)
if checked['raw_content'] is not None:
    storage_markdown = checked['raw_content']
    # Pass storage_markdown and checked status/findings to Trista.
else:
    # Persist only IDs/status/category-only findings if needed.
    # Do not persist the original Markdown, even for manual review.
    pass
```

`raw_content` is filtered Markdown suitable under this limited policy, NOT an
unaltered Firecrawl original. `approved` means no supported detector fired;
it does not certify absence of sensitive information. `redacted` means entire
contact-bearing paragraphs were removed. `needs_review` and `blocked` return
`raw_content=None`, no cleaned body and no chunks in the processing entry point.
A reviewer must supply a newly sanitized input; merely changing the status is
not a review workflow. There is no persistent quarantine in this implementation.

Run the check on the original in memory before cleaning, so removing boilerplate
cannot conceal a sensitive finding. Never log incoming payloads or exceptions
containing their contents. Findings expose categories only, not values or spans.

## Trista: process the original in memory once

```python
from apps.api.services.processing import process_document

result = process_document({
    'document_id': 'doc_1',
    'source_id': 'source_1',
    'raw_content': '# Alex\n\nEnjoys hiking.\n\nContact alex@example.test',
    'metadata': {'url': 'https://example.com/about', 'title': 'About Alex'},
})
```

Result (all content here is fictional):

```json
{
  "document_id": "doc_1",
  "source_id": "source_1",
  "raw_content": "# Alex\n\nEnjoys hiking.",
  "cleaned_text": "# Alex\n\nEnjoys hiking.",
  "sensitivity_status": "redacted",
  "findings": [{"category": "email"}],
  "chunks": [{
    "chunk_index": 0,
    "document_id": "doc_1",
    "source_id": "source_1",
    "text": "# Alex\n\nEnjoys hiking.",
    "fts_text": "# Alex\n\nEnjoys hiking.",
    "start_char": 0,
    "end_char": 22,
    "evidence_basis": "filtered_text"
  }]
}
```

Persist only returned `raw_content` and `cleaned_text` when content is allowed.
Use returned chunk text for `claim_sources.excerpt`. Offsets refer to the filtered
`cleaned_text`, never original Markdown. Keep the `redacted` provenance when
rendering evidence; do not label it a verbatim original quote. If Emily already
filtered a document, retain her original status/findings separately: reprocessing
safe text cannot recover the fact that redaction occurred.

The input metadata is intentionally not copied into the result. URLs, titles,
other Firecrawl fields, source records and content hashes are a separate storage
boundary: Emily/Trista must inspect these too before persistence (including URL
query secrets). This function filters Markdown only. Do not serialize the whole
incoming document next to the filtered result.

## Chunk and FTS integration

`max_chars=1000` is configurable. Paragraph/title boundaries are preferred; long
paragraphs split at whitespace, then character boundaries for long tokens.
Concatenating chunk `text` reproduces cleaned text exactly. Whitespace is retained
for this purpose; separator-only tails attach to their preceding chunk, so the
size is a target rather than an absolute bound. Long tables/code/links can cross
chunk boundaries; offsets permit fetching surrounding filtered context. There
are no invented redaction markers to fragment.

```python
import sqlite3
from apps.api.services.retrieval import ChunkSearch

connection = sqlite3.connect(':memory:')
index = ChunkSearch(connection)
index.replace_document(project_id='project_1', result=result)
hits = index.search('hiking', project_id='project_1', source_ids=['source_1'])
connection.close()
```

Hits include `document_id`, `source_id`, `chunk_index`, filtered `excerpt` and
`evidence_basis`. The caller must resolve trusted project/source ownership and
the subject's allowed source IDs before calling; this adapter is not an API
authorization layer. Both scopes are applied in SQL. Denied replacements remove
old entries for the same project/document. Reindex on status/content changes.

`ChunkSearch` creates only `temp.processing_fts` on the supplied connection.
It is disposable and must be rebuilt per connection. Its transaction commits on
replacement, so use a dedicated connection rather than one with a pending
application transaction. No migrations, persistent tables or storage API were
added. Once Trista provides persistent FTS, map returned chunks into it and retain
the same project/source restrictions and status exclusions.

## Current connection status and limitations

Cleaner → sensitivity → chunk output and chunk output → temporary FTS are tested
locally (sensitivity runs first). Firecrawl, storage routes, persistent FTS and
workers are currently empty and are NOT connected. The older database document
uses `documents.content`; the agreed `raw_content` / `cleaned_text` /
`document_chunks` schema still belongs to Trista. The older Firecrawl pipeline
places storage before inspection: integrators must move inspection before any
raw-body write. No production schema or other teammate's API was changed.

Detection separates category patterns from status policy. Supported heuristics
cover conventional emails/phone-like numbers, labeled credentials and financial
identifiers, some token prefixes, English health/finance/location cues,
coordinates and selected ambiguous contact expressions. Percent decoding and
HTML entity decoding help inspect Markdown link destinations. No Presidio or
language model is installed; there were no existing dependencies to reuse.

These heuristics miss unfamiliar credentials, obfuscation, images, indirect
medical facts, unlabeled addresses and many languages/context variants. Numeric
IDs/dates may be over-redacted as phone candidates. Health/finance words may
hold educational content for review. Removing an entire paragraph can discard
useful adjacent facts and disrupt a Markdown construct spanning paragraphs.
No site-specific boilerplate rules ship without samples; callers may supply
confirmed exact lines, which are not removed inside fenced/indented code.

FTS5 `unicode61` uses literal AND terms, without stemming or synonyms.
Verified English examples: `HIKING` matches `Hiking`; `hike` does not.
`robots` matches `robots`; `robot` does not. `creative projects` requires both
terms. The adapter returns no invented evidence for unmatched queries.
Non-English search quality is outside the supported scope.
