"""Тесты пользовательских настроек из GUI (runtime_settings).

Файл настроек подменяется на временный каталог, реальные данные не трогаются.
Запуск: python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import runtime_settings  # noqa: E402


class RuntimeSettingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_path = runtime_settings.SETTINGS_PATH
        runtime_settings.SETTINGS_PATH = os.path.join(self._tmp.name, 'settings.json')
        runtime_settings._cache = None

    def tearDown(self):
        runtime_settings.SETTINGS_PATH = self._orig_path
        runtime_settings._cache = None
        self._tmp.cleanup()

    def test_default_model_comes_from_config(self):
        self.assertEqual(runtime_settings.get_llm_model(), config.LLM_MODEL)
        self.assertEqual(runtime_settings.get_settings(), {})

    def test_saved_model_is_persisted(self):
        runtime_settings.set_llm_model('qwen2.5:7b')
        self.assertTrue(os.path.exists(runtime_settings.SETTINGS_PATH))

        # Сбрасываем кэш - значение должно прочитаться с диска
        runtime_settings._cache = None
        self.assertEqual(runtime_settings.get_llm_model(), 'qwen2.5:7b')
        self.assertEqual(runtime_settings.get_settings()['llm_model'], 'qwen2.5:7b')

    def test_empty_model_is_rejected(self):
        with self.assertRaises(ValueError):
            runtime_settings.set_llm_model('   ')
        self.assertEqual(runtime_settings.get_llm_model(), config.LLM_MODEL)

    def test_reset_restores_default(self):
        runtime_settings.set_llm_model('mistral:7b')
        runtime_settings.reset()
        self.assertEqual(runtime_settings.get_llm_model(), config.LLM_MODEL)


if __name__ == '__main__':
    unittest.main()
