"""Disposable connection-local FTS5 adapter; never creates production tables."""
import re
import sqlite3
from .sensitivity import prepare_for_storage


class ChunkSearch:
    """Caller must obtain project/source ownership from its trusted DB layer.

    Use one connection per corpus snapshot. Rebuild after reconnecting.
    """
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        connection.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS temp.processing_fts
            USING fts5(project_id UNINDEXED, source_id UNINDEXED,
                       document_id UNINDEXED, chunk_index UNINDEXED, text,
                       tokenize='unicode61')''')

    def replace_document(self, *, project_id: str, result: dict) -> None:
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError('project_id is required')
        doc_id, source_id = result['document_id'], result['source_id']
        rows = []
        if result['sensitivity_status'] in {'approved', 'redacted'}:
            for chunk in result['chunks']:
                if chunk['document_id'] != doc_id or chunk['source_id'] != source_id:
                    raise ValueError('chunk ownership mismatch')
                if prepare_for_storage(chunk['text'])['sensitivity_status'] != 'approved':
                    raise ValueError('chunk has not passed filtering')
                rows.append((project_id, source_id, doc_id, chunk['chunk_index'], chunk['text']))
        with self.connection:
            self.connection.execute('DELETE FROM temp.processing_fts WHERE project_id=? AND document_id=?', (project_id, doc_id))
            self.connection.executemany('INSERT INTO temp.processing_fts VALUES (?,?,?,?,?)', rows)

    def search(self, query: str, *, project_id: str, source_ids: list[str], limit: int = 5) -> list[dict]:
        """Both project and explicit subject source allowlist are mandatory."""
        if not project_id or not source_ids:
            return []
        if not 1 <= limit <= 100:
            raise ValueError('limit must be between 1 and 100')
        terms = re.findall(r'[^\W_]+', query, flags=re.UNICODE)
        if not terms:
            return []
        expression = ' AND '.join('"' + term + '"' for term in terms)
        placeholders = ','.join('?' for _ in source_ids)
        rows = self.connection.execute(f'''SELECT document_id, source_id, chunk_index, text
            FROM temp.processing_fts WHERE processing_fts MATCH ? AND project_id=?
            AND source_id IN ({placeholders}) ORDER BY bm25(processing_fts), document_id, chunk_index LIMIT ?''',
            (expression, project_id, *source_ids, limit)).fetchall()
        return [dict(document_id=d, source_id=s, chunk_index=int(i), excerpt=t,
                     evidence_basis='filtered_text') for d, s, i, t in rows]
