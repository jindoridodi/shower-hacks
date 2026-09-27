# Instagram/Apify Live Verification

Use this checklist only with an approved public demo account. Never commit an Apify token, raw upstream payload, profile image, or downloaded media.

## Configuration

Set these values in the local `.env` file:

```text
APIFY_API_TOKEN=your-local-token
APIFY_INSTAGRAM_ACTOR=apify~instagram-profile-scraper
APIFY_INSTAGRAM_TIMEOUT_SECONDS=90
INSTAGRAM_USE_FIXTURES=false
```

The adapter sends the token through the `Authorization: Bearer` header. It uses Apify's synchronous Actor dataset endpoint with one username, `maxItems=1`, `clean=true`, and a 90-second run timeout. The synchronous endpoint supports runs up to five minutes; this application intentionally sets a shorter bound for the demo. See [Apify's synchronous Actor API reference](https://docs.apify.com/api/v2/actor-run-sync-get-dataset-items-get).

## Record after one approved test

- Date:
- Approved public demo username:
- Actor ID and build tag:
- HTTP result:
- Returned normalized fields:
- Missing or changed upstream fields:
- Known limitations or rate-limit behavior:

Confirm that no token was logged, no media was downloaded, and the returned profile did not create or queue a crawl source.
