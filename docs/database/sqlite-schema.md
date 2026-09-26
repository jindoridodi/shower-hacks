# SQLite Schema

```sql
CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  url TEXT NOT NULL,
  canonical_url TEXT,
  title TEXT,
  source_type TEXT NOT NULL,
  scraped_at TEXT,
  content_hash TEXT,
  status TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  content TEXT NOT NULL,
  sensitivity_status TEXT NOT NULL,
  FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE TABLE claims (
  id TEXT PRIMARY KEY,
  report_id TEXT NOT NULL,
  text TEXT NOT NULL,
  claim_type TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE claim_sources (
  claim_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  excerpt TEXT NOT NULL,
  PRIMARY KEY (claim_id, source_id)
);
```
