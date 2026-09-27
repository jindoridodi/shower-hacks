def create_project(client, name="Portrait", description="Public pages"):
    response = client.post(
        "/projects",
        json={"name": name, "description": description},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_source(client, project_id, url="https://example.com/about"):
    response = client.post("/sources", json={"project_id": project_id, "url": url})
    assert response.status_code == 201, response.text
    return response.json()


def approve_source(client, source_id):
    response = client.patch(
        f"/sources/{source_id}/approval", json={"approval_status": "approved"}
    )
    assert response.status_code == 200, response.text
    return response.json()
