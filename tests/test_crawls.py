from tests.helpers import create_project, create_source


def test_crawl_job_tracks_status_timestamps_and_errors(client):
    project = create_project(client)
    source = create_source(client, project["id"])

    created = client.post("/crawls", json={"source_id": source["id"]})
    assert created.status_code == 201
    job = created.json()
    assert job["status"] == "queued"
    assert job["error_message"] is None
    assert job["started_at"] is None
    assert job["completed_at"] is None

    queued_source = client.get(f"/sources/{source['id']}")
    assert queued_source.json()["status"] == "queued"

    running = client.patch(f"/crawls/{job['id']}", json={"status": "running"})
    assert running.status_code == 200
    assert running.json()["status"] == "running"
    assert running.json()["started_at"]
    assert running.json()["completed_at"] is None

    missing_error = client.patch(f"/crawls/{job['id']}", json={"status": "failed"})
    assert missing_error.status_code == 422
    assert missing_error.json()["detail"]["code"] == "error_message_required"

    failed = client.patch(
        f"/crawls/{job['id']}",
        json={"status": "failed", "error_message": "Public page returned 404"},
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["error_message"] == "Public page returned 404"
    assert failed.json()["completed_at"]

    source_after = client.get(f"/sources/{source['id']}").json()
    assert source_after["status"] == "failed"
    assert source_after["scraped_at"] is None

    blocked = client.post("/crawls", json={"source_id": source["id"]})
    assert blocked.status_code == 201
    second = blocked.json()

    backward = client.patch(f"/crawls/{job['id']}", json={"status": "running"})
    assert backward.status_code == 409
    assert backward.json()["detail"]["code"] == "invalid_status_transition"

    active = client.post("/sources/{}/queue".format(source["id"]))
    assert active.status_code == 409
    assert active.json()["detail"]["code"] == "crawl_already_active"

    succeeded = client.patch(f"/crawls/{second['id']}", json={"status": "running"})
    assert succeeded.status_code == 200
    done = client.patch(f"/crawls/{second['id']}", json={"status": "succeeded"})
    assert done.status_code == 200
    assert done.json()["completed_at"]
    finished_source = client.get(f"/sources/{source['id']}").json()
    assert finished_source["status"] == "succeeded"
    assert finished_source["scraped_at"] == done.json()["completed_at"]

    listed = client.get("/crawls", params={"source_id": source["id"]})
    assert [item["id"] for item in listed.json()] == [job["id"], second["id"]]


def test_queue_endpoint_creates_a_crawl(client):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/queue")
    queued = client.post(f"/sources/{source['id']}/queue")
    assert queued.status_code == 201
    assert queued.json()["status"] == "queued"
    assert client.get(f"/sources/{source['id']}").json()["status"] == "queued"


def test_crawl_for_missing_source_returns_404(client):
    response = client.post("/crawls", json={"source_id": "missing-source"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "source_not_found"


def test_succeeded_crawl_rejects_an_error_message(client):
    project = create_project(client)
    source = create_source(client, project["id"], "https://example.com/ok")
    job = client.post("/crawls", json={"source_id": source["id"]}).json()
    client.patch(f"/crawls/{job['id']}", json={"status": "running"})
    response = client.patch(
        f"/crawls/{job['id']}",
        json={"status": "succeeded", "error_message": "should not stick"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "error_message_not_allowed"
