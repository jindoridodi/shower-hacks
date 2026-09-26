import pytest
from sqlalchemy import text

from apps.api.errors import APIError
from apps.api.services.crawls import ingest_scraped_page
from apps.api.services.documents import search_chunks as backend_search
from apps.api.services.firecrawl import ScrapedPage
from apps.api.services.retrieval import search_chunks
from tests.helpers import create_project, create_source


def test_real_fts5_search_scoping_limits_and_filtered_evidence(client, session):
    expected = []
    for index in range(2):
        project = create_project(client, name=f'Project {index}')
        source = create_source(client, project['id'], f'https://example.com/{index}')
        job = client.post('/crawls', json={'source_id': source['id']}).json()
        document = ingest_scraped_page(session, job['id'], ScrapedPage(
            url=source['url'], markdown='Hiking robots.\n\nBuilds creative projects.\n\nhidden@example.test',
        ))
        expected.append((project['id'], source['id'], document.id))
    ddl = session.execute(text("SELECT sql FROM sqlite_master WHERE name='document_chunks_fts'")).scalar()
    assert 'fts5' in ddl.lower()
    hits = search_chunks(session, 'hiking')
    assert hits == backend_search(session, 'hiking')
    assert {hit.document_id for hit in hits} == {item[2] for item in expected}
    assert len(search_chunks(session, 'hiking', limit=1)) == 1
    for project_id, source_id, document_id in expected:
        hit, = search_chunks(session, 'hiking', project_id=project_id)
        assert (hit.document_id, hit.source_id, hit.chunk_index) == (document_id, source_id, 0)
        assert '@' not in hit.text
        assert search_chunks(session, 'hidden', project_id=project_id) == []
    for term, count in [('HIKING', 2), ('hike', 0), ('robots', 2), ('robot', 0),
                        ('creative projects', 2), ('" OR *', 0)]:
        assert len(search_chunks(session, term)) == count
    with pytest.raises(APIError) as error:
        search_chunks(session, '***')
    assert error.value.payload['code'] == 'invalid_search'
    with pytest.raises(APIError) as error:
        search_chunks(session, 'hiking', project_id='missing')
    assert error.value.payload['code'] == 'project_not_found'


def test_retrieval_preserves_existing_backend_unreviewed_behavior(client, session):
    project = create_project(client)
    source = create_source(client, project['id'])
    response = client.post('/documents', json={
        'source_id': source['id'], 'cleaned_text': 'Existing biography',
        'chunks': [{'chunk_index': 0, 'text': 'Existing biography'}],
    })
    assert response.status_code == 201
    assert response.json()['sensitivity_status'] == 'unreviewed'
    hit, = search_chunks(session, 'biography')
    assert hit.document_id == response.json()['id']
    session.execute(text('UPDATE document_chunks SET text=:body WHERE id=:id'),
                    {'body': 'Updated gardening', 'id': hit.id})
    session.commit()
    assert search_chunks(session, 'biography') == []
    updated, = search_chunks(session, 'gardening')
    assert updated.id == hit.id
    assert updated.text == 'Updated gardening'
    session.execute(text('DELETE FROM documents WHERE id=:id'), {'id': hit.document_id})
    session.commit()
    assert search_chunks(session, 'biography') == []
    assert search_chunks(session, 'gardening') == []
    assert session.execute(text('SELECT count(*) FROM document_chunks_fts')).scalar() == 0
