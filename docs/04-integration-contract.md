# Integration Contract

## API endpoints

```text
POST /api/projects
POST /api/projects/{project_id}/sources
POST /api/projects/{project_id}/crawls
GET  /api/crawls/{crawl_id}
GET  /api/projects/{project_id}/sources
GET  /api/projects/{project_id}/corpus
POST /api/projects/{project_id}/reports
POST /api/projects/{project_id}/drafts
GET  /api/reports/{report_id}
GET  /api/health
```

## Crawl response

```json
{
  "crawl_id": "crawl_001",
  "status": "queued",
  "source_count": 3,
  "error": null
}
```

## Error response

```json
{
  "error": {
    "code": "CRAWL_FAILED",
    "message": "The page could not be retrieved.",
    "retryable": true
  }
}
```

Keep endpoint names and response fields stable after frontend integration starts.
