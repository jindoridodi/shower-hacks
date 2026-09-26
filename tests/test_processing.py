import json
import sqlite3
import unittest
from uuid import UUID
from apps.api.services.cleaner import clean_markdown
from apps.api.services.chunker import chunk_text
from apps.api.services.processing import process_document
from apps.api.services.sensitivity import prepare_for_storage
from apps.api.services.retrieval import ChunkSearch


def process(text, doc='doc_1', source='src_1', **kwargs):
    return process_document(dict(document_id=doc, source_id=source, raw_text=text), **kwargs)


class ProcessingTests(unittest.TestCase):
    def test_generated_document_ids(self):
        document = {'source_id': 'src_1', 'raw_text': 'Hiking. ' * 20}
        first = process_document(document, max_chars=30)
        second = process_document({**document, 'document_id': None})
        self.assertEqual(UUID(first['document_id']).version, 4)
        self.assertEqual(UUID(second['document_id']).version, 4)
        self.assertNotEqual(first['document_id'], second['document_id'])
        self.assertNotIn('document_id', document)
        self.assertGreater(len(first['chunks']), 1)
        for chunk in first['chunks']:
            self.assertEqual(chunk['document_id'], first['document_id'])
            self.assertEqual(chunk['source_id'], 'src_1')

    def test_supplied_document_id(self):
        self.assertEqual(process('Hiking', doc='existing_doc')['document_id'], 'existing_doc')
        for invalid in ('', '   ', 123):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                process('Hiking', doc=invalid)

    def test_markdown_structure(self):
        text = '# Alex\n\n- Hiking\n- Cookies are a hobby\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n[Project](https://example.com)\n![Mountain](mountain.png)\n\n```python\nx = 1  \n\n\n```\n\n    indented  '
        self.assertEqual(clean_markdown(text), text)
        self.assertEqual(clean_markdown('A\r\n\r\n\r\nB   '), 'A\n\nB  ')

    def test_confirmed_boilerplate_only(self):
        self.assertEqual(clean_markdown('Menu\n\nI write about cookies.\n\nMenu', confirmed_boilerplate=('Menu',)), 'I write about cookies.')
        self.assertEqual(clean_markdown('```\nMenu\n```', confirmed_boilerplate=('Menu',)), '```\nMenu\n```')

    def test_contact_never_reappears(self):
        result = process('# Alex\n\nEnjoys hiking.\n\nContact [Alex](mailto:alex%40example.test).\n\nCall +1 (202) 555-0142.\n\nBuilds robots.')
        self.assertEqual(result['sensitivity_status'], 'redacted')
        for secret in ('alex%40', '555-0142', 'Contact', 'Call'):
            self.assertNotIn(secret, json.dumps(result))
        self.assertIn('robots', result['cleaned_text'])

    def test_sensitive_blocks_redacted(self):
        cases = [('password: fictional-secret', 'redacted'),
                 ('api_key=sk-fictional123456789', 'redacted'),
                 ('bank account: 12345678', 'redacted'),
                 ('Alex was diagnosed with a fictional condition.', 'redacted'),
                 ('His medication is fictional.', 'redacted'),
                 ('Her salary is 42 coins.', 'redacted'),
                 ('Home address: 123 Fiction Lane.', 'redacted'),
                 ('Coordinates 37.12345, 127.12345', 'redacted'),
                 ('alex [at] example.test', 'redacted'),
                 ('password instructions\n\nalex@example.test', 'redacted')]
        for raw, status in cases:
            with self.subTest(status=status):
                result = process(raw)
                self.assertEqual(result['sensitivity_status'], status)
                self.assertIsNone(result['raw_text'])
                self.assertEqual(result['cleaned_text'], '')
                self.assertEqual(result['chunks'], [])
                self.assertNotIn(raw, json.dumps(result))
                mixed = process('Enjoys hiking.\n\n' + raw + '\n\nBuilds robots.')
                self.assertEqual(mixed['sensitivity_status'], 'redacted')
                self.assertEqual(mixed['raw_text'], 'Enjoys hiking.\n\nBuilds robots.')
                self.assertEqual(mixed['cleaned_text'], mixed['raw_text'])
                self.assertEqual(''.join(c['text'] for c in mixed['chunks']), mixed['cleaned_text'])

    def test_empty_and_all_removed(self):
        for text in ('', ' \n\t', 'alex@example.test'):
            result = process(text)
            self.assertEqual(result['sensitivity_status'], 'redacted' if '@' in text else 'clear')
            self.assertEqual(result['chunks'], [])
            self.assertIsNone(result['raw_text'])

    def test_lossless_long_chunks(self):
        for text in ('# Topic\n\n' + 'Hiking robots. ' * 500, 'x' * 4001, ' ' * 30 + 'abc\n\nxyz'):
            for size in (1, 17, 1000):
                chunks = chunk_text(text, document_id='d', source_id='s', sensitivity_status='clear', max_chars=size)
                self.assertEqual(''.join(c['text'] for c in chunks), text)
                for index, c in enumerate(chunks):
                    self.assertTrue(c['text'].strip())
                    self.assertEqual(c['chunk_index'], index)
                    self.assertEqual((c['document_id'], c['source_id']), ('d', 's'))
                    self.assertEqual(c['text'], text[c['start_char']:c['end_char']])

    def test_clear_and_unreviewed(self):
        self.assertEqual(process('Hiking')['sensitivity_status'], 'clear')

    def test_denied_chunking(self):
        for status in ('unreviewed', 'unknown'):
            self.assertEqual(chunk_text('text', document_id='d', source_id='s', sensitivity_status=status), [])
        with self.assertRaises(ValueError):
            process('text', max_chars=0)


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.index = ChunkSearch(self.db)

    def test_scope_evidence_and_literal_query(self):
        for project, doc, source in [('p1', 'd1', 's1'), ('p2', 'd2', 's2'), ('p1', 'd3', 's3')]:
            self.index.replace_document(project_id=project, result=process('Hiking robots\n\nalex@example.test', doc, source))
        hits = self.index.search('hiking', project_id='p1', source_ids=['s1'])
        self.assertEqual(len(hits), 1)
        self.assertEqual((hits[0]['document_id'], hits[0]['source_id']), ('d1', 's1'))
        self.assertNotIn('@', hits[0]['excerpt'])
        self.assertEqual(self.index.search('example', project_id='p1', source_ids=['s1']), [])
        self.assertEqual(self.index.search('hiking', project_id='p1', source_ids=['s2']), [])
        self.assertEqual(self.index.search('hiking', project_id='p1', source_ids=[]), [])
        self.assertEqual(self.index.search('" OR *', project_id='p1', source_ids=['s1']), [])

    def test_denied_replacement_removes_old_rows(self):
        for raw in ('Her salary is 42 coins.', 'password: fictional'):
            self.index.replace_document(project_id='p', result=process('Hiking'))
            self.index.replace_document(project_id='p', result=process(raw))
            self.assertEqual(self.index.search('hiking', project_id='p', source_ids=['src_1']), [])

    def test_unreviewed_not_indexed(self):
        result = process('Hiking')
        result['sensitivity_status'] = 'unreviewed'
        self.index.replace_document(project_id='p', result=result)
        self.assertEqual(self.index.search('hiking', project_id='p', source_ids=['src_1']), [])

    def test_english_token_limits(self):
        self.index.replace_document(project_id='p', result=process('Hiking robots.\n\nBuilds creative projects.'))
        for term, expected in [('HIKING', True), ('hike', False), ('robots', True), ('creative projects', True), ('robot', False)]:
            self.assertEqual(bool(self.index.search(term, project_id='p', source_ids=['src_1'])), expected)

    def test_reject_unfiltered_and_wrong_ownership(self):
        result = process('Hiking')
        result['chunks'][0]['text'] = 'alex@example.test'
        with self.assertRaises(ValueError):
            self.index.replace_document(project_id='p', result=result)
        result = process('Hiking')
        result['chunks'][0]['source_id'] = 'other'
        with self.assertRaises(ValueError):
            self.index.replace_document(project_id='p', result=result)


if __name__ == '__main__':
    unittest.main()
