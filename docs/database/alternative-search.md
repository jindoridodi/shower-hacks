# Alternative Search Backends

SQLite FTS5 is the required MVP search layer. Consider these only when the corpus outgrows the demo:

- **Meilisearch:** simple hosted or local full-text search.
- **OpenSearch:** larger searchable corpus and analytics.
- **Qdrant:** dedicated vector search.
- **Chroma:** lightweight local semantic search.

The application should keep the retrieval interface stable so a backend can be swapped without changing the frontend or report schema.
