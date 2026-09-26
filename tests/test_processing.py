import json
import unittest
from apps.api.services.sensitivity import prepare_for_storage
from apps.api.services.cleaner import clean_markdown
from apps.api.services.chunker import chunk_text
from apps.api.services.processing import process_document


def process(text, doc='doc_1', source='src_1', **kwargs):
    return process_document(dict(document_id=doc, source_id=source, raw_text=text), **kwargs)


class ProcessingTests(unittest.TestCase):
    def test_metadata_preserved(self):
        metadata = {'url': 'https://example.com/about?topic=hiking', 'title': 'About Alex', 'extra': 'not copied'}
        result = process_document({'document_id': 'db_doc', 'source_id': 's', 'raw_text': 'Hiking', 'metadata': metadata})
        self.assertEqual(result['metadata'], {k: metadata[k] for k in ('url', 'title')})
        self.assertEqual(result['metadata_findings'], [])
        self.assertEqual(result['sensitivity_status'], 'clear')
        self.assertIn('extra', metadata)
        self.assertEqual(process('Hiking')['metadata'], {})

    def test_sensitive_metadata_omitted(self):
        for url in ('https://example.com/?token=fictionalvalue',
                    'https://user:fictionalvalue@example.com',
                    'https://example.com/?email=alex%40example.test',
                    'javascript:alert(1)'):
            result = process_document({'document_id': 'db_doc', 'source_id': 's', 'raw_text': 'Hiking',
                                       'metadata': {'url': url, 'title': 'Contact alex@example.test'}})
            self.assertEqual(result['metadata'], {})
            self.assertEqual(result['sensitivity_status'], 'redacted')
            self.assertEqual(result['cleaned_text'], 'Hiking')
            self.assertTrue(result['chunks'])
            self.assertNotIn('fictionalvalue', json.dumps(result))
            self.assertNotIn('alex@', json.dumps(result))
            self.assertEqual({f['field'] for f in result['metadata_findings']}, {'url', 'title'})
        result = process_document({'document_id': 'db_doc', 'source_id': 's', 'raw_text': 'Hiking',
                                   'metadata': {'url': 'https://example.com', 'title': 'Her salary is private'}})
        self.assertEqual(result['metadata'], {'url': 'https://example.com'})

    def test_invalid_metadata(self):
        for metadata in ([], {'title': 123}, {'url': {}}):
            with self.assertRaises(TypeError):
                process_document({'document_id': 'db_doc', 'source_id': 's', 'raw_text': 'Hiking', 'metadata': metadata})

    def test_database_document_id_required(self):
        document = {'source_id': 'src_1', 'raw_text': 'Hiking. ' * 20}
        with self.assertRaisesRegex(ValueError, 'document_id'):
            process_document(document)
        for invalid in (None, '', '   ', 123):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'document_id'):
                process_document({**document, 'document_id': invalid})
        document['document_id'] = 'db_existing_doc'
        original = document.copy()
        result = process_document(document, max_chars=30)
        self.assertEqual(document, original)
        self.assertEqual(result['document_id'], 'db_existing_doc')
        self.assertGreater(len(result['chunks']), 1)
        for chunk in result['chunks']:
            self.assertEqual(chunk['document_id'], 'db_existing_doc')
            self.assertEqual(chunk['source_id'], 'src_1')

    def test_invalid_document_input(self):
        with self.assertRaisesRegex(TypeError, 'dictionary'):
            process_document(None)
        with self.assertRaisesRegex(ValueError, 'source_id'):
            process_document({'document_id': 'db_doc', 'raw_text': 'Hiking'})
        with self.assertRaisesRegex(ValueError, 'raw_text'):
            process_document({'document_id': 'db_doc', 'source_id': 's'})

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


if __name__ == '__main__':
    unittest.main()
