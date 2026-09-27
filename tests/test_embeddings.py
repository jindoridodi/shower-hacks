"""Deterministic integration tests; no model download or inference dependency."""
import math
import sys
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from apps.api.config import Settings
from apps.api.errors import APIError
from apps.api.main import create_app
from apps.api.models import ChunkEmbedding, DocumentChunk
from apps.api.services.embeddings import prepare_embeddings, stage_embeddings, unit_vector
from tests.helpers import approve_source, create_project, create_source


class FakeEmbedder:
    dimensions = 3

    def __init__(self):
        self.calls = []

    def embed_documents(self, texts):
        self.calls.extend(texts)
        return [[1., 0., 0.] if 'hiking' in t.lower() else [0., 1., 0.] for t in texts]

    def embed_query(self, query):
        return [1., 0., 0.] if 'outdoor' in query.lower() else [0., 1., 0.]


@contextmanager
def running(tmp_path, *, enabled=True, provider=None, filename='embeddings.db'):
    settings = Settings(_env_file=None, embeddings_enabled=enabled, embedding_model_revision='test-revision')
    app = create_app(tmp_path / filename, settings=settings, embedding_provider=provider or FakeEmbedder())
    try:
        with TestClient(app) as client:
            yield app, client
    finally:
        app.state.engine.dispose()


def add_document(client, source_id, body):
    response = client.post('/documents', json={
        'source_id': source_id, 'cleaned_text': body, 'sensitivity_status': 'clear',
        'chunks': [{'chunk_index': 0, 'text': body}],
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_same_api_uses_semantic_search_and_project_scope(tmp_path):
    provider = FakeEmbedder()
    with running(tmp_path, provider=provider) as (app, client):
        p1 = create_project(client)
        p2 = create_project(client, name='Other')
        s1 = create_source(client, p1['id'])
        s2 = create_source(client, p2['id'], 'https://example.com/other')
        d1 = add_document(client, s1['id'], 'Alex enjoys hiking.')
        d2 = add_document(client, s2['id'], 'Casey enjoys hiking.')
        with app.state.session_factory() as db:
            vectors = db.scalars(select(ChunkEmbedding)).all()
            assert len(vectors) == 2
            assert all(v.dimensions == 3 and math.isclose(math.hypot(*v.vector_json), 1.) for v in vectors)
        hits = client.get('/search/chunks', params={'q': 'outdoor hobbies', 'project_id': p1['id']}).json()
        assert [h['document_id'] for h in hits] == [d1['id']]
        assert hits[0]['source_id'] == s1['id']
        assert set(hits[0]) == {'id', 'document_id', 'source_id', 'chunk_index', 'text'}
        global_hits = client.get('/search/chunks', params={'q': 'outdoor hobbies', 'limit': 1})
        assert global_hits.status_code == 200 and len(global_hits.json()) == 1
        assert client.get('/search/chunks', params={'q': 'outdoor', 'project_id': 'missing'}).status_code == 404
        assert d2['id'] != d1['id']


def test_disabled_uses_fts_without_loading_model(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('disabled mode tried to load an embedder')
    monkeypatch.setattr('apps.api.services.embeddings._cached_provider', forbidden)
    with running(tmp_path, enabled=False) as (app, client):
        assert app.state.embeddings_prepared == 0
        project = create_project(client)
        source = create_source(client, project['id'])
        add_document(client, source['id'], 'Alex enjoys hiking.')
        assert client.get('/search/chunks', params={'q': 'hiking'}).json()
        assert client.get('/search/chunks', params={'q': 'outdoor hobbies'}).json() == []
        with app.state.session_factory() as db:
            assert db.scalar(select(func.count()).select_from(ChunkEmbedding)) == 0


def test_startup_backfills_once_and_reuses_vectors(tmp_path):
    with running(tmp_path, enabled=False) as (_, client):
        project = create_project(client)
        source = create_source(client, project['id'])
        add_document(client, source['id'], 'Hiking is a hobby.')
    provider = FakeEmbedder()
    with running(tmp_path, provider=provider) as (app, client):
        assert app.state.embeddings_prepared == 1
        assert len(provider.calls) == 1
        assert client.get('/search/chunks', params={'q': 'outdoor hobbies'}).json()
        with app.state.session_factory() as db:
            assert prepare_embeddings(db) == 0
        assert len(provider.calls) == 1
    with running(tmp_path, provider=provider) as (app, _):
        assert app.state.embeddings_prepared == 0
        assert len(provider.calls) == 1


def test_missing_stale_and_invalid_vectors_are_reported(tmp_path):
    with running(tmp_path) as (app, client):
        project = create_project(client)
        source = create_source(client, project['id'])
        doc = add_document(client, source['id'], 'Hiking')
        with app.state.session_factory() as db:
            chunk = db.scalar(select(DocumentChunk))
            # The trigger must invalidate a vector when its associated text changes.
            chunk.text = 'Gardening'
            db.commit()
            assert db.get(ChunkEmbedding, chunk.id) is None
        response = client.get('/search/chunks', params={'q': 'outdoor'})
        assert response.status_code == 503
        assert response.json()['detail']['code'] == 'embeddings_not_ready'
        with app.state.session_factory() as db:
            assert prepare_embeddings(db) == 1
            row = db.scalar(select(ChunkEmbedding))
            row.vector_json = [0., 0., 0.]
            db.commit()
        response = client.get('/search/chunks', params={'q': 'outdoor'})
        assert response.json()['detail']['code'] == 'invalid_embedding'
        with app.state.session_factory() as db:
            assert prepare_embeddings(db) == 1  # Repair corrupt vector data too.
            row = db.scalar(select(ChunkEmbedding))
            row.model_revision = 'obsolete'
            db.commit()
            assert prepare_embeddings(db) == 1
        assert client.get('/search/chunks', params={'q': 'outdoor'}).status_code == 200
        assert doc['id']


def test_model_failure_stops_startup(tmp_path, monkeypatch):
    def fail(*args):
        raise APIError(503, 'embedding_model_unavailable', 'Model unavailable')
    monkeypatch.setattr('apps.api.services.embeddings._cached_provider', fail)
    app = create_app(tmp_path / 'failure.db', settings=Settings(_env_file=None, embeddings_enabled=True))
    try:
        with pytest.raises(APIError, match='Model unavailable'):
            with TestClient(app):
                pass
    finally:
        app.state.engine.dispose()


def test_invalid_model_output_rolls_back_new_document(tmp_path):
    class Invalid(FakeEmbedder):
        def embed_documents(self, texts):
            return [[1., 2.] for _ in texts]
    with running(tmp_path, provider=Invalid()) as (app, client):
        project = create_project(client)
        source = create_source(client, project['id'])
        response = client.post('/documents', json={
            'source_id': source['id'], 'cleaned_text': 'Hiking',
            'chunks': [{'chunk_index': 0, 'text': 'Hiking'}],
        })
        assert response.status_code == 503
        with app.state.session_factory() as db:
            assert db.scalar(select(func.count()).select_from(DocumentChunk)) == 0
            assert db.scalar(select(func.count()).select_from(ChunkEmbedding)) == 0


def test_incremental_chunk_api_and_vector_cascade(tmp_path):
    with running(tmp_path) as (app, client):
        project = create_project(client)
        source = create_source(client, project['id'])
        doc = add_document(client, source['id'], 'Hiking')
        response = client.post(f"/documents/{doc['id']}/chunks", json={
            'chunks': [{'chunk_index': 1, 'text': 'Gardening'}],
        })
        assert response.status_code == 201
        with app.state.session_factory() as db:
            assert db.scalar(select(func.count()).select_from(ChunkEmbedding)) == 2
            chunk = db.get(DocumentChunk, response.json()[0]['id'])
            db.delete(chunk)
            db.commit()
            assert db.scalar(select(func.count()).select_from(ChunkEmbedding)) == 1


def test_ingest_embeds_filtered_text_only(tmp_path):
    from apps.api.services.crawls import ingest_scraped_page
    from apps.api.services.firecrawl import ScrapedPage
    provider = FakeEmbedder()
    with running(tmp_path, provider=provider) as (app, client):
        project = create_project(client)
        source = create_source(client, project['id'])
        approve_source(client, source['id'])
        response = client.post('/crawls', json={'source_id': source['id']})
        assert response.status_code == 201, response.text
        job = response.json()
        with app.state.session_factory() as db:
            document = ingest_scraped_page(db, job['id'], ScrapedPage(
                url=source['url'], markdown='Enjoys hiking.\n\nContact alex@example.test',
            ))
            assert document.sensitivity_status == 'redacted'
            assert db.scalar(select(func.count()).select_from(ChunkEmbedding)) == 1
        assert provider.calls == ['Enjoys hiking.']


@pytest.mark.parametrize('vector', [[0, 0], [float('nan'), 1], [float('inf'), 1], [1], [True, 1]])
def test_vector_validation(vector):
    with pytest.raises(APIError):
        unit_vector(vector, 2)


def test_bge_checks_token_limit_and_query_instruction(monkeypatch):
    """Exercise real adapter control flow using a fake model, without ML imports."""
    from types import SimpleNamespace
    from apps.api.services.embeddings import BGEEmbedder, QUERY_PREFIX
    class Model:
        max_seq_length = 20
        def __init__(self, *args, **kwargs):
            self.encoded = []
        def get_sentence_embedding_dimension(self): return 2
        def tokenizer(self, texts, **kwargs): return {'length': [len(t.split()) + 2 for t in texts]}
        def encode(self, texts, **kwargs):
            self.encoded.extend(texts)
            return SimpleNamespace(tolist=lambda: [[3., 4.] for _ in texts])
    monkeypatch.setitem(sys.modules, 'sentence_transformers', SimpleNamespace(SentenceTransformer=Model))
    embedder = BGEEmbedder(Settings(_env_file=None))
    assert embedder.embed_documents(['Hiking']) == [[0.6, 0.8]]
    assert embedder.embed_query('outdoor hobbies') == [0.6, 0.8]
    assert embedder.model.encoded == ['Hiking', QUERY_PREFIX + 'outdoor hobbies']
    with pytest.raises(APIError) as caught:
        embedder.embed_documents(['hiking ' * 30])
    assert caught.value.payload['code'] == 'embedding_input_too_long'
    assert len(embedder.model.encoded) == 2
