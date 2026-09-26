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
