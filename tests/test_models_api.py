"""Тесты API управления моделями (models_api).

Сеть не используется: Ollama-адрес указывает на заведомо закрытый порт,
а «скачанная» модель Whisper подкладывается вручную в временный каталог.

Запуск: python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flask  # noqa: E402

import models_api  # noqa: E402


def make_client(model_dir, active=None):
    state = active if active is not None else {'model': 'gemma3'}
    application = flask.Flask(__name__)
    application.register_blueprint(models_api.create_blueprint(
        model_dir=model_dir,
        default_model_size='small',
        llm_model='gemma3',
        ollama_url='http://127.0.0.1:9',  # заведомо закрытый порт: Ollama «недоступна»
        allowed_sizes={'tiny', 'base', 'small', 'medium', 'large', 'large-v3'},
        ffmpeg_path='/nonexistent/ffmpeg',
        active_model_getter=lambda: state['model'],
        active_model_setter=lambda name: state.__setitem__('model', name),
    ))
    return application.test_client()


class RecommendSizeTests(unittest.TestCase):
    def test_small_pc_gets_small_model(self):
        self.assertEqual(models_api.recommend_whisper_size(4), 'base')
        self.assertEqual(models_api.recommend_whisper_size(8), 'small')

    def test_big_pc_gets_large_model(self):
        self.assertEqual(models_api.recommend_whisper_size(16), 'large-v3')

    def test_unknown_memory_is_conservative(self):
        self.assertEqual(models_api.recommend_whisper_size(0), 'base')


class ModelsApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.model_dir = os.path.join(self._tmp.name, 'models')
        os.makedirs(self.model_dir, exist_ok=True)
        self.client = make_client(self.model_dir)

    def tearDown(self):
        self._tmp.cleanup()

    def _fake_model(self, size):
        path = os.path.join(self.model_dir, size)
        os.makedirs(path, exist_ok=True)
        for name in ('model.bin', 'config.json'):
            with open(os.path.join(path, name), 'wb') as fh:
                fh.write(b'x' * 16)

    def test_setup_reports_structure(self):
        data = self.client.get('/api/setup').get_json()
        for key in ('platform', 'ffmpeg', 'whisper', 'ollama', 'recommended_size',
                    'ready', 'warnings', 'memory_gb'):
            self.assertIn(key, data)
        self.assertIsInstance(data['warnings'], list)
        self.assertFalse(data['ollama']['running'])
        self.assertIsInstance(data['whisper']['catalog'], list)
        self.assertTrue(len(data['whisper']['catalog']) >= 5)

    def test_setup_sees_local_model(self):
        self._fake_model('small')
        data = self.client.get('/api/setup').get_json()
        self.assertIn('small', data['whisper']['local_sizes'])
        self.assertTrue(data['whisper']['default_ready'])
        self.assertNotIn('Модель Whisper', ' '.join(data['warnings']))

    def test_models_catalog(self):
        data = self.client.get('/api/models').get_json()
        sizes = [item['size'] for item in data['whisper']['catalog']]
        self.assertIn('medium', sizes)
        self.assertEqual(data['ollama']['model'], 'gemma3')
        self.assertFalse(data['ollama']['running'])

    def test_download_rejects_unknown_size(self):
        response = self.client.post('/api/models/whisper/download', json={'size': 'gigantic'})
        self.assertEqual(response.status_code, 400)

    def test_download_already_present(self):
        self._fake_model('tiny')
        response = self.client.post('/api/models/whisper/download', json={'size': 'tiny'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['already'])

    def test_pull_rejects_bad_model_name(self):
        response = self.client.post('/api/models/ollama/pull', json={'model': '../evil'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/models/ollama/pull', json={'model': ''})
        self.assertEqual(response.status_code, 400)

    def test_models_use_saved_active_model(self):
        self.client = make_client(self.model_dir, active={'model': 'qwen2.5:7b'})
        data = self.client.get('/api/models').get_json()
        self.assertEqual(data['ollama']['model'], 'qwen2.5:7b')
        self.assertFalse(data['ollama']['model_ready'])

    def test_set_active_rejects_bad_name(self):
        response = self.client.post('/api/models/ollama/active', json={'model': '../evil'})
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/models/ollama/active', json={})
        self.assertEqual(response.status_code, 400)

    def test_import_requires_http_url(self):
        for payload in ({'url': ''}, {'url': 'file:///etc/passwd'}, {'url': 'ftp://x/y.gguf'}):
            response = self.client.post('/api/models/ollama/import', json=payload)
            self.assertEqual(response.status_code, 400, payload)

    def test_import_rejects_empty_model_name(self):
        response = self.client.post('/api/models/ollama/import',
                                    json={'url': 'https://example.com/model.gguf', 'name': '!!!'})
        self.assertEqual(response.status_code, 400)

    def test_tasks_endpoint_is_dict(self):
        data = self.client.get('/api/models/tasks').get_json()
        self.assertIsInstance(data, dict)


if __name__ == '__main__':
    unittest.main()
