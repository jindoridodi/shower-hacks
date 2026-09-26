"""Use main's persistent FTS5 search and its existing optional project scope.

Requires main's SQLAlchemy services at integration time; no temporary index or
additional sensitivity/source restrictions are applied here.
"""


def search_chunks(db, query: str, *, project_id: str | None = None, limit: int = 20):
    from .documents import search_chunks as main_search_chunks

    return main_search_chunks(db, query, project_id=project_id, limit=limit)
