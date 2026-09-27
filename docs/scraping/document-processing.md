# Document processing handoff (Sehyun)

The pure processing functions use the Python standard library. Database integration
uses the existing SQLAlchemy/SQLite backend; no API keys or network calls are required.
English is the supported language for this pipeline: detection rules, examples,
status/error messages and search validation use English. There is no automatic
translation or language rejection. Unicode source text is preserved, but
non-English contextual sensitivity detection is unsupported.

Run from repository root:

```sh
pip install -e ".[dev]"
pytest
python -m unittest discover -s tests -t . -v
```

Optional external discovery CLIs retain their existing adapters and can be installed
with `pip install -e ".[dev,osint]"` on a platform supported by their dependencies.
They are not required to run the API, fixture providers, or these tests.

## Emily: inspect BEFORE storing or logging

```python
from apps.api.services.sensitivity import prepare_for_storage

checked = prepare_for_storage(markdown)
if checked['raw_text'] is not None:
    storage_markdown = checked['raw_text']
    # Pass storage_markdown and checked status/findings to Trista.
else:
    # Persist only IDs/status/category-only findings if needed.
    # Do not persist the original Markdown, even for manual review.
    pass
```

`raw_text` is filtered Markdown suitable under this limited policy, NOT an
unaltered Firecrawl original. `clear` means no supported detector fired;
it does not certify absence of sensitive information. `redacted` means content
was removed: any blank-line-delimited block containing a detected category is
removed, including credentials and contextual candidates. Other blocks remain.
Detection runs per block; context spanning separate blocks may be missed.
When no usable blocks remain, processing returns
`raw_text=None`, an empty cleaned body and no chunks. Skip document persistence
when `raw_text` is None; the production schema requires a nonempty body.
`unreviewed` means not yet inspected and is never returned by the inspection
function. Processing does not create chunks for it. Main search keeps its existing
behavior and does not apply an additional sensitivity-status filter. There is no manual-review state.
Empty input without findings is `clear`, but has no usable body or chunks.

Run the check on the original in memory before cleaning, so removing boilerplate
cannot conceal a sensitive finding. Never log incoming payloads or exceptions
containing their contents. Findings expose categories only, not values or spans.

## Trista: process the original in memory once

`document_id` is required and must be a nonempty string supplied by the DB
integration layer. Missing, null or invalid IDs raise ValueError. The function
never generates IDs, queries the DB, or verifies that an ID exists; the caller
must also verify source ownership. The result and its chunks preserve the ID.

For main's current insert-generated IDs, inspect/filter the body and metadata
BEFORE stage_document, skip empty filtered bodies, and store only filtered data.
Then use the returned document.id for chunking the prepared text within the same
transaction. Never store unfiltered content just to obtain an ID. If processing
is repeated, keep original redaction findings/status; sanitized input alone
cannot reconstruct them. Reused documents from deduplication also use their
existing DB ID. This integration is now wired into main ingest_scraped_page.
prepare_document performs filtering once before the insert; chunk_text receives the
returned DB ID, prepared text and original inspection status. Findings are retained
on the document instead of re-detecting them from sanitized text.
Only newly created documents get new chunks; deduplicated documents retain their
existing chunks and stored metadata. Historical content is not reprocessed.

```python
from apps.api.services.processing import process_document

result = process_document({
    'document_id': 'doc_1',
    'source_id': 'source_1',
    'raw_text': '# Alex\n\nEnjoys hiking.\n\nContact alex@example.test',
    'metadata': {'url': 'https://example.com/about', 'title': 'About Alex'},
})
```

Result (all content here is fictional):

```json
{
  "document_id": "doc_1",
  "source_id": "source_1",
  "raw_text": "# Alex\n\nEnjoys hiking.",
  "cleaned_text": "# Alex\n\nEnjoys hiking.",
  "sensitivity_status": "redacted",
  "findings": [{"category": "email"}],
  "metadata": {"url": "https://example.com/about", "title": "About Alex"},
  "metadata_findings": [],
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

Persist only returned `raw_text` and `cleaned_text` when content is allowed.
Use returned chunk text for `claim_sources.excerpt`. Offsets refer to the filtered
`cleaned_text`, never original Markdown. Keep the `redacted` provenance when
rendering evidence; do not label it a verbatim original quote. If Emily already
filtered a document, retain her original status/findings separately: reprocessing
safe text cannot recover the fact that redaction occurred.

Input `metadata.url` and `metadata.title` are inspected and preserved in the
result's `metadata` object. Missing metadata produces `{}`. Other keys are omitted.
A detected value is omitted entirely, never partially rewritten; rejected URL
schemes, URL credentials and recognized secret query keys are also omitted.
`metadata_findings` records field/category labels only. Removal marks the overall
result `redacted` while usable body text and chunks remain available.
The detectors are heuristic: arbitrary opaque URL secrets can still be missed.
This is not URL authorization or crawl allowlist enforcement.

When integrating, pass the safe title to the document record and resolve URL
ownership through the existing source_id. Other Firecrawl metadata and source
records still require inspection before persistence. Do not store the incoming
payload alongside the filtered output.

The standalone tests in `tests/test_sensitivity.py` and `tests/test_processing.py`
cover filtering, normalization, metadata, offsets and lossless reconstruction.
`tests/test_ingestion.py` checks writes, rejected pages, database IDs, deduplication
and rollback. `tests/test_retrieval.py` exercises the real SQLite FTS5 backend.
The existing backend tests remain in place and run with pytest.

## Chunk and FTS integration

`max_chars=1000` is configurable. Paragraph/title boundaries are preferred; long
paragraphs split at whitespace, then character boundaries for long tokens.
Concatenating chunk `text` reproduces cleaned text exactly. Whitespace is retained
for this purpose; separator-only tails attach to their preceding chunk, so the
size is a target rather than an absolute bound. Long tables/code/links can cross
chunk boundaries; offsets permit fetching surrounding filtered context. There
are no invented redaction markers to fragment.

The main ChunkCreate API preserves leading/trailing whitespace and rejects
whitespace-only chunks. Join generated chunks in chunk_index order with
`"".join(chunk.text for chunk in chunks)` to retain original spaces and newlines.
Do not add spaces indiscriminately: long tokens can cross chunk boundaries.

Production retrieval uses main's existing documents.search_chunks:

```python
from apps.api.services.documents import search_chunks
hits = search_chunks(db, 'hiking', project_id='project_1')
```

It returns chunk ID, document ID, source ID, chunk_index and text. project_id is
optional; omitting it searches all projects. There is no additional source-ID
allowlist or sensitivity-status filter. This retains main's existing behavior.
The standalone retrieval.py now delegates to this function and requires main's
services and SQLAlchemy session; the temporary ChunkSearch API was removed.

## Current connection status and limitations

Main's ingest_scraped_page calls prepare_document before any document write,
stores only filtered Markdown and title, and creates chunks with the DB ID
inside the same transaction. Raw HTML is not persisted in this path. The existing `raw_path` field points to
a file containing only filtered Markdown; rejected bodies create no file.
Duplicate documents keep their existing file. A database commit failure after
a file write may leave an unreferenced filtered file; it never contains rejected text. Empty or
fully removed input returns None, creates no document/chunks, marks job/source
failed and records a fixed reason without rejected content. Callers must handle
None; retries can queue another crawl. Processing errors roll back the insert.
Source URLs are existing source records; this path does not rewrite them.
Direct /documents writes retain main's existing behavior and do not automatically
run the scraper processing pipeline. Migration 003 adds document columns for `processing_metadata`,
`sensitivity_findings` and `metadata_findings`, also exposed by DocumentRead. These
contain filtered metadata and category labels only; existing rows default to empty
objects/lists. The same migration corrects FTS5 update/delete triggers for the
existing standalone index, preserving search synchronization. Deduplication retains the original stored provenance. Offsets remain
in the pure processing result and refer to cleaned text, not source HTML.
The existing policy-enforced Firecrawl scraper and worker entry point are preserved.
This change adds no network calls or embeddings, and tests use injected local fakes.

Detection separates category patterns from status policy. Supported heuristics
cover conventional emails/phone-like numbers, labeled credentials and financial
identifiers, some token prefixes, English health/finance/location cues,
coordinates and selected ambiguous contact expressions. Percent decoding and
HTML entity decoding help inspect Markdown link destinations. No Presidio or language model is used in this processing path.

These heuristics miss unfamiliar credentials, obfuscation, images, indirect
medical facts, unlabeled addresses and many languages/context variants. Numeric
IDs/dates may be over-redacted as phone candidates. Health/finance words may
remove educational content as a false positive. Removing an entire paragraph can discard
useful adjacent facts and disrupt a Markdown construct spanning paragraphs.
No site-specific boilerplate rules ship without samples; callers may supply
confirmed exact lines, which are not removed inside fenced/indented code.

FTS5 `unicode61` uses literal AND terms, without stemming or synonyms.
Verified English examples: `HIKING` matches `Hiking`; `hike` does not.
`robots` matches `robots`; `robot` does not. `creative projects` requires both
terms. Search returns no invented evidence for unmatched queries.
Non-English search quality is outside the supported scope.
