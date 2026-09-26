# Scraping Failure Handling

## User-visible states

`queued` · `crawling` · `processing` · `complete` · `partial` · `failed`

## Behavior

- Retry transient failures once.
- Preserve successful pages when some pages fail.
- Show failed URLs and reasons.
- Offer fixture data for the live demo.
- Never silently substitute unrelated content.
