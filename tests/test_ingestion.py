import json

import pytest
from sqlalchemy import event, func, select, text

from apps.api.models import Document, DocumentChunk
from apps.api.services import crawls
from apps.api.services.documents import list_chunks
from apps.api.services.firecrawl import ScrapedPage
from apps.api.services.retrieval import search_chunks
from tests.helpers import create_project, create_source


def queued_page(client):
    project = create_project(client)
    source = create_source(client, project['id'], 'https://example.com/about')
    job = client.post('/crawls', json={'source_id': source['id']}).json()
    return source, job


def test_filtering_precedes_every_database_write(client, session, app):
    source, job = queued_page(client)
    writes = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(('INSERT', 'UPDATE')):
            writes.append(repr(parameters))

    event.listen(app.state.engine, 'before_cursor_execute', capture)
    try:
        document = crawls.ingest_scraped_page(session, job['id'], ScrapedPage(
            url=source['url'],
            markdown='# Biography\n\nEnjoys hiking.\n\nContact hidden@example.test\n\nBuilds robots.',
            title='Contact hidden@example.test',
            raw_html='<p>password: html-only-secret</p>',
        ))
    finally:
        event.remove(app.state.engine, 'before_cursor_execute', capture)
    assert document is not None
    session.expire_all()
    stored = client.get(f'/documents/{document.id}').json()
    assert stored['sensitivity_status'] == 'redacted'
    assert stored['sensitivity_findings'] == [{'category': 'email'}]
    assert stored['metadata_findings'] == [{'field': 'title', 'category': 'email'}]
    assert stored['processing_metadata'] == {'url': source['url']}
    assert stored['title'] is None
    assert stored['raw_text'] == '# Biography\n\nEnjoys hiking.\n\nBuilds robots.'
    chunks = list_chunks(session, document.id)
    assert ''.join(c.text for c in chunks) == stored['cleaned_text']
    assert search_chunks(session, 'hiking')[0].document_id == document.id
    assert search_chunks(session, 'hidden') == []
    dump = json.dumps(stored) + repr(writes) + repr([c.text for c in chunks])
    for rejected in ('hidden@example.test', 'html-only-secret'):
        assert rejected not in dump


@pytest.mark.parametrize('body', ['', ' \n\t ', 'password: rejected-secret', 'hidden@example.test'])
@pytest.mark.parametrize('running', [False, True])
def test_rejected_pages_store_no_document_or_index_rows(client, session, body, running):
    source, job = queued_page(client)
    if running:
        crawls.update_crawl_status(session, job['id'], 'running', None)
    result = crawls.ingest_scraped_page(session, job['id'], ScrapedPage(
        url=source['url'], markdown=body, title='Contact hidden@example.test',
        raw_html='<p>rejected-secret</p>',
    ))
    assert result is None
    assert session.scalar(select(func.count()).select_from(Document)) == 0
    assert session.scalar(select(func.count()).select_from(DocumentChunk)) == 0
    assert session.execute(text('SELECT count(*) FROM document_chunks_fts')).scalar() == 0
    stored_job = client.get(f"/crawls/{job['id']}").json()
    assert stored_job['status'] == 'failed'
    assert stored_job['completed_at']
    assert stored_job['error_message'] == 'No usable content remains after document processing'
    stored_source = client.get(f"/sources/{source['id']}").json()
    assert stored_source['status'] == 'failed'
    assert stored_source['content_hash'] is None
    assert client.post('/crawls', json={'source_id': source['id']}).status_code == 201


def test_chunks_use_inserted_document_id_and_reconstruct_text(client, session, monkeypatch):
    source, job = queued_page(client)
    original = crawls.chunk_text
    observed = []

    def check_database_id(body, **kwargs):
        document = session.get(Document, kwargs['document_id'])
        assert document is not None
        assert document.source_id == kwargs['source_id'] == source['id']
        chunks = original(body, **kwargs)
        observed.extend(chunks)
        return chunks

    monkeypatch.setattr(crawls, 'chunk_text', check_database_id)
    document = crawls.ingest_scraped_page(session, job['id'], ScrapedPage(
        url=source['url'], markdown='# Hiking\r\n\r\n' + 'Builds robots. ' * 300,
    ))
    chunks = list_chunks(session, document.id)
    assert len(chunks) > 1
    assert [c.text for c in chunks] == [c['text'] for c in observed]
    assert ''.join(c.text for c in chunks) == document.cleaned_text
    for index, chunk in enumerate(observed):
        assert chunk['document_id'] == document.id
        assert chunk['start_char'] == (observed[index - 1]['end_char'] if index else 0)
        assert chunk['text'] == document.cleaned_text[chunk['start_char']:chunk['end_char']]
    assert observed[-1]['end_char'] == len(document.cleaned_text)


def test_dedup_retains_existing_id_chunks_and_redaction_provenance(client, session):
    source, job = queued_page(client)
    first = crawls.ingest_scraped_page(session, job['id'], ScrapedPage(
        url=source['url'], markdown='Hiking robots\n\nhidden@example.test',
        title='Contact hidden@example.test',
    ))
    first_id = first.id
    chunk_ids = [c.id for c in list_chunks(session, first_id)]
    original = client.get(f'/documents/{first_id}').json()
    # A different snapshot changes the source hash before the old body is seen again.
    job2 = client.post('/crawls', json={'source_id': source['id']}).json()
    crawls.ingest_scraped_page(session, job2['id'], ScrapedPage(
        url=source['url'], markdown='Gardening notes',
    ))
    job3 = client.post('/crawls', json={'source_id': source['id']}).json()
    duplicate = crawls.ingest_scraped_page(session, job3['id'], ScrapedPage(
        url=source['url'], markdown='Hiking robots', title='New safe title',
    ))
    assert duplicate.id == first_id
    assert client.get(f'/documents/{first_id}').json() == original
    assert [c.id for c in list_chunks(session, first_id)] == chunk_ids
    assert session.scalar(select(func.count()).select_from(Document)) == 2
    assert len(search_chunks(session, 'hiking')) == 1
    assert client.get(f"/sources/{source['id']}").json()['content_hash'] == first.content_hash
    assert client.get(f"/crawls/{job3['id']}").json()['status'] == 'succeeded'


def test_chunk_failure_rolls_back_document_source_job_and_fts(client, session, monkeypatch):
    source, job = queued_page(client)
    original = crawls.stage_chunks

    def fail_after_chunks(*args):
        original(*args)
        session.flush()
        raise RuntimeError('Synthetic chunk failure')

    monkeypatch.setattr(crawls, 'stage_chunks', fail_after_chunks)
    with pytest.raises(RuntimeError, match='Synthetic chunk failure'):
        crawls.ingest_scraped_page(session, job['id'], ScrapedPage(
            url=source['url'], markdown='Hiking robots',
        ))
    assert session.scalar(select(func.count()).select_from(Document)) == 0
    assert session.scalar(select(func.count()).select_from(DocumentChunk)) == 0
    assert search_chunks(session, 'hiking') == []
    assert client.get(f"/crawls/{job['id']}").json()['status'] == 'queued'
    assert client.get(f"/sources/{source['id']}").json()['content_hash'] is None


def test_url_metadata_findings_survive_database_reload(client, session):
    source, job = queued_page(client)
    document = crawls.ingest_scraped_page(session, job['id'], ScrapedPage(
        url=source['url'] + '#token=fictionalvalue', markdown='Hiking robots', title='About',
    ))
    session.expire_all()
    stored = client.get(f'/documents/{document.id}').json()
    assert stored['sensitivity_status'] == 'redacted'
    assert stored['processing_metadata'] == {'title': 'About'}
    assert stored['metadata_findings'] == [{'field': 'url', 'category': 'url_secret'}]
    assert stored['sensitivity_findings'] == []
    assert 'fictionalvalue' not in json.dumps(stored)
    assert len(search_chunks(session, 'hiking')) == 1
