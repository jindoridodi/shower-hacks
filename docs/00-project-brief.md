# Project Brief

## One-sentence description

An evidence-linked web artwork that turns a small set of public webpages into a portrait, then exposes how much of that portrait is observation, inference, uncertainty, and borrowed language.

## Demo promise

In under two minutes, a visitor submits public URLs, watches a corpus form, receives a source-linked report, and inspects the evidence behind every claim.

## Must-have features

- Public URL input
- Firecrawl ingestion
- SQLite persistence
- Source-linked claims
- Factual profile or relationship summary
- Uncertainty and contradiction display
- One clearly labeled communication draft requiring manual review

## Out of scope

- Private-account access or access-control bypasses
- Voice or writing-style imitation
- Invented facts, memories, or quotes
- Automatic sending, posting, or emailing
- Sensitive data in model prompts

## Success criteria

- A clean end-to-end demo works from a fresh restart.
- Every generated claim has at least one source excerpt.
- Unsupported claims are rejected or labeled unknown.
- The demo survives a crawl failure using fixture data.
