from apps.api.services.crawls import claim_next_queued_crawl, run_claimed_crawl
from apps.api.services.firecrawl import ScrapedPage
from tests.helpers import approve_source, create_project, create_source


class FixtureScraper:
    def scrape_public_url(self, url: str) -> ScrapedPage:
        return ScrapedPage(url=url, markdown="# Public page\n\nSafe fixture content.", title="Fixture")


def test_worker_claims_and_completes_only_an_approved_queued_crawl(client, session):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/worker")

    assert client.post("/crawls", json={"source_id": source["id"]}).status_code == 409
    assert claim_next_queued_crawl(session) is None

    approve_source(client, source["id"])
    queued = client.post("/crawls", json={"source_id": source["id"]}).json()
    claimed = claim_next_queued_crawl(session)
    assert claimed is not None
    assert claimed.id == queued["id"]
    assert claimed.status == "running"

    document = run_claimed_crawl(session, claimed.id, FixtureScraper())
    assert document.title == "Fixture"
    assert client.get(f"/crawls/{claimed.id}").json()["status"] == "succeeded"


def test_rejecting_a_source_removes_it_from_the_crawl_allowlist(client):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/rejected")
    approve_source(client, source["id"])

    rejected = client.patch(
        f"/sources/{source['id']}/approval", json={"approval_status": "rejected"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["is_allowlisted"] is False
    assert client.post("/crawls", json={"source_id": source["id"]}).status_code == 409
