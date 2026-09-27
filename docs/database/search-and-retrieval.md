# Search and Retrieval

## MVP

Use SQLite FTS5 to retrieve excerpts by keyword and source ID.

## Optional semantic search

Add `sqlite-vec` only after the keyword path works. The report generator must receive source IDs and excerpts regardless of search method.

## Checklist

- [ ] Return top-k excerpts.
- [ ] Preserve source IDs.
- [ ] Deduplicate near-identical excerpts.
- [ ] Prefer attributable text.
- [ ] Return an empty result rather than inventing support.


## Optional BGE search

Install the optional runtime once:

```sh
pip install -e ".[embeddings]"
```

Configure `.env`, then restart the server:

```text
EMBEDDINGS_ENABLED=true
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_MODEL_REVISION=5c38ec7c405ec4b44b94cc5a9bb96e735b38267a
EMBEDDING_BATCH_SIZE=16
```

Run with a single process for the small demo:

```sh
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers 1
```

The flag is read at process startup. False uses the existing FTS5 path and never
loads ML dependencies. True loads BGE on CPU and backfills missing, stale or invalid
vectors during FastAPI lifespan startup, before accepting requests. There is no
standalone backfill script, fallback to FTS5, hybrid search or RRF.

`GET /search/chunks?q=outdoor+hobbies&project_id=...&limit=5` uses the same parameters
and response fields in both modes: chunk ID, document ID, source ID, index and text.
Project scope remains optional, matching main. There is no new sensitivity status
filter or source allowlist. Semantic mode scores every chunk in the selected scope;
it returns nearest candidates, not verified evidence or a relevance guarantee.
No universal cosine threshold is assumed. A nonempty corpus usually returns hits
even for an unrelated query, unlike literal keyword FTS5.

BGE adds its retrieval instruction to queries only, validates input token count
(including special and instruction tokens), and rejects overlong inputs rather
than truncating. It creates 384-dimensional normalized vectors; dot products are
cosine similarities. Current chunks use character lengths, which do not guarantee
fewer than 512 model tokens. Overlong historical chunks stop startup with
`embedding_input_too_long`; use smaller chunks and reindex. No text is dropped or
silently re-chunked.

The new chunk_embeddings table stores chunk ID, pinned model/revision, dimension,
chunk text hash, JSON vector and timestamp. Legacy document_chunks.embedding stays
unchanged. A text edit invalidates its vector, a deletion cascades to it, and startup
rebuilds outdated entries. Switching back to false retains vectors for future use.
Model revision changes trigger re-embedding without mixing incompatible vectors.

New chunks created by crawl ingestion, POST /documents, and POST chunk batches
are embedded through stage_chunks when enabled. This is synchronous in the caller's
transaction: inference failure rolls back the write, and workers retain their
existing failure handling. Keep batches/corpora small; inference adds write latency
and startup backfill delays readiness. Multiple workers each load a model copy.
No distributed queue or vector database was added. Search is exhaustive Python
cosine scoring, intended for a small corpus.

Missing runtime/model, invalid model outputs, or stale vectors produce explicit
errors; enabled mode never silently switches to keyword search. The model may
need network access on the first load; EMBEDDING_CACHE_DIR can point to a persistent
cache. Startup failures occur before health checks can succeed.

Sources: [BGE model card](https://huggingface.co/BAAI/bge-small-en-v1.5),
[Sentence Transformers API](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html).
