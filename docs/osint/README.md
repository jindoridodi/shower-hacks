# OSINT Workstream

## Goal

Suggest publicly visible URLs without making discovery a core dependency. The application must work from manually supplied URLs.

## Checklist

- [ ] Accept a username or URL.
- [ ] Return candidate URLs with type and confidence.
- [ ] Deduplicate candidates.
- [ ] Require candidates to enter the crawl allowlist.
- [ ] Return no private-account content.
- [ ] Produce fixture results if discovery is unavailable.

## Tools

- Sherlock or Maigret for username suggestions.
- Manual URL input as the primary fallback.
