import json
import unittest
from apps.api.services.sensitivity import prepare_for_storage


class SensitivityTests(unittest.TestCase):
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
                result = prepare_for_storage(raw)
                self.assertEqual(result['sensitivity_status'], status)
                self.assertIsNone(result['raw_text'])
                self.assertNotIn(raw, json.dumps(result))
                mixed = prepare_for_storage('Enjoys hiking.\n\n' + raw + '\n\nBuilds robots.')
                self.assertEqual(mixed['sensitivity_status'], 'redacted')
                self.assertEqual(mixed['raw_text'], 'Enjoys hiking.\n\nBuilds robots.')


if __name__ == '__main__':
    unittest.main()
