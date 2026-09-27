# Integration Contract

## API endpoints

```text
POST /api/projects
GET  /api/projects
POST /instagram/profiles
POST /api/discovery
POST /api/graph/export?format=csv|gexf
POST /api/enrichment/spiderfoot
GET  /api/enrichment/spiderfoot/{job_id}
POST /api/projects/{project_id}/sources
GET  /api/projects/{project_id}/sources?username={username}
DELETE /api/projects/{project_id}/sources/{source_id}
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

## Discovery response

`POST /api/discovery` returns candidate public URLs only. It never crawls or generates reports. The endpoint infers a direct URL from an `http://` or `https://` query; every other query is handled as a username. `queryType` remains accepted for backward compatibility. When the optional `projectId` is provided for a username query, it also merges locally saved user-supplied sources for that exact project and normalized username.

```json
{
  "query": "demo-user",
  "candidates": [],
  "providersUsed": ["sherlock", "maigret", "whatsmyname"],
  "providerEvidence": {},
  "savedSources": [],
  "partial": false,
  "warnings": []
}
```

Username discovery always runs Sherlock, Maigret, and WhatsMyName. Empty candidates are a successful result; provider failures use `partial` and `warnings`. Saved sources carry `user_supplied` evidence and high confidence because they were deliberately attached, not because they prove identity.

`POST /api/projects/{project_id}/sources` accepts `{ "username": "demo-user", "url": "https://example.com/profile" }`. URLs must be direct public HTTP(S) URLs; saving does not fetch, crawl, or enrich them.

`POST /api/graph/export` accepts the discovery `query`, `candidates`, and `providerEvidence`, then returns a CSV ZIP or GEXF download. SpiderFoot enrichment only accepts an explicitly selected public URL, username, or domain and never starts a crawl.

## Instagram profile response

`POST /instagram/profiles` accepts one public Instagram username:

```json
{ "username": "example.user" }
```

It returns normalized profile fields: `username`, `full_name`, `biography`, `profile_url`, `profile_picture_url`, `external_url`, `category`, profile counts, `is_verified`, `is_private`, and up to ten caption-bearing `recent_posts`. URLs remain strings; the endpoint does not download media, create sources, or queue crawls.

For private profiles, only the username, canonical profile URL, private/verified flags, and available counts are returned. Name, biography, image, external URL, category, and posts are redacted to `null` or `[]`.

Errors use the normal API `detail` envelope with `code`, `message`, and `retryable`:

| Status | Code | Retryable |
| --- | --- | --- |
| 503 | `apify_not_configured` | no |
| 503 | `apify_auth_failed` | no |
| 404 | `instagram_profile_not_found` | no |
| 503 | `instagram_provider_unavailable` | yes |
| 502 | `instagram_invalid_response` | no |
| 502 | `instagram_provider_rejected` | no |

Set `INSTAGRAM_USE_FIXTURES=true` to use `demo.public`, `demo.private`, `demo.missing`, and `demo.unavailable` from `data/fixtures/instagram-profiles.json`. Fixture mode is explicit and never replaces a failed live lookup.
