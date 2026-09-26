# Firecrawl Pipeline

## MVP request

```json
{
  "url": "https://example.com",
  "limit": 10,
  "maxDepth": 1,
  "scrapeOptions": {
    "formats": ["markdown", "links"],
    "onlyMainContent": true
  }
}
```

## Processing

1. Validate the URL scheme.
2. Check the project allowlist.
3. Submit the Firecrawl job.
4. Poll or receive completion.
5. Normalize Markdown.
6. Store metadata and content hash.
7. Run sensitivity detection.
8. Index safe chunks.
