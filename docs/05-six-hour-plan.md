# Six-Hour Build Plan

## 00:00–00:30 — Freeze scope

- [ ] Choose prepared demo URLs.
- [ ] Confirm output modes.
- [ ] Confirm SQLite schema and endpoint names.
- [ ] Assign owners and backups.
- [ ] Create fixture data.

## 00:30–02:00 — Vertical slices

- [ ] Firecrawl ingests one URL.
- [ ] SQLite stores one source and document.
- [ ] Retrieval returns one excerpt.
- [ ] Generation returns one cited claim.
- [ ] Frontend displays one result.

## 02:00–03:30 — Integrate

- [ ] URL input reaches the API.
- [ ] Crawl status reaches the frontend.
- [ ] Crawled content reaches SQLite.
- [ ] Reports use real excerpts.
- [ ] Source ledger is clickable.

## 03:30–04:30 — Make it legible

- [ ] Add observed/inferred/uncertain labels.
- [ ] Add contradictions and unknowns.
- [ ] Add draft review state.
- [ ] Add loading and empty states.
- [ ] Improve opening and final screens.

## 04:30–06:00 — Harden, freeze, rehearse

- [ ] Test invalid URLs and crawl failures.
- [ ] Test empty corpus and missing keys.
- [ ] Confirm clean restart and fixture fallback.
- [ ] Stop feature work.
- [ ] Run the demo three times.
- [ ] Commit and tag `demo-final`.
