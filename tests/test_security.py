"""Тесты защиты токеном (ACCESS_TOKEN) и файлового лога.

Запуск: python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # noqa: E402


class AccessTokenTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self._original = app.ACCESS_TOKEN

    def tearDown(self):
        app.set_access_token(self._original)

    def test_no_token_configured_is_open(self):
        app.set_access_token('')
        self.assertEqual(self.client.get('/health').status_code, 200)

    def test_token_required(self):
        app.set_access_token('secret')
        self.assertEqual(self.client.get('/health').status_code, 401)

    def test_token_via_header(self):
        app.set_access_token('secret')
        response = self.client.get('/health', headers={'X-Access-Token': 'secret'})
        self.assertEqual(response.status_code, 200)

    def test_token_via_query_sets_cookie(self):
        app.set_access_token('secret')
        response = self.client.get('/health?token=secret')
        self.assertEqual(response.status_code, 200)
        self.assertIn('cutline_token', response.headers.get('Set-Cookie', ''))

    def test_wrong_token_rejected(self):
        app.set_access_token('secret')
        self.assertEqual(self.client.get('/health?token=nope').status_code, 401)


class LoggingTests(unittest.TestCase):
    def test_log_file_created(self):
        # _configure_logging создаёт logs/cutline.log при импорте app
        log_path = os.path.join(app.LOG_DIR, 'cutline.log')
        self.assertTrue(os.path.isdir(app.LOG_DIR))
        self.assertTrue(os.path.exists(log_path))


if __name__ == '__main__':
    unittest.main()
