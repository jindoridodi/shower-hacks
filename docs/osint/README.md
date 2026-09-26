# OSINT Workstream

See [implementation-plan.md](implementation-plan.md) for the discovery MVP and [extended-providers-plan.md](extended-providers-plan.md) for the always-on Maigret, WhatsMyName, SpiderFoot, and Gephi extension.

## Goal

Search public username-profile sources and suggest candidate URLs. Manual public URLs remain supported as a separate direct-input path.

## Checklist

- [x] Accept a username or URL.
- [x] Search Sherlock, Maigret, and WhatsMyName for every username query.
- [x] Return candidate URLs with type, confidence, and provider evidence.
- [x] Deduplicate candidates.
- [ ] Require candidates to enter the crawl allowlist.
- [ ] Return no private-account content.
- [x] Produce deterministic fixture results for offline demos and tests.

## Tools

- Sherlock, Maigret, and WhatsMyName for every username query.
- Namechk for quick username/domain presence checks.
- Gephi CSV/GEXF export for offline relationship graphs.
- SpiderFoot for selected-source public correlation, with invasive modules disabled.
- Manual URL input for direct public-source discovery.

## Recommended order

1. Sherlock, Maigret, and WhatsMyName discovery
2. Source validation
3. Gephi export or explicitly selected SpiderFoot enrichment
4. Add approved candidates to the crawl allowlist

Do not automatically run SpiderFoot or Firecrawl from discovery; both require an explicit source-selection action.
