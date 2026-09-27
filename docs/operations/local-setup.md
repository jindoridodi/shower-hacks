# Local Setup

## Requirements

- Node.js 20+
- Python 3.11+
- SQLite 3 with FTS5
- Firecrawl API key
- LLM API key or Ollama
- Apify API token for live Instagram profile lookups (optional in fixture mode)

## Checklist

- [ ] Install frontend dependencies.
- [ ] Create a Python virtual environment.
- [ ] Copy `.env.example` to `.env`.
- [ ] Set `APIFY_API_TOKEN` for live Instagram lookup, or set `INSTAGRAM_USE_FIXTURES=true` for deterministic local fixtures.
- [ ] Initialize SQLite.
- [ ] Seed fixtures.
- [ ] Start API.
- [ ] Start frontend.
- [ ] Open the health endpoint.
