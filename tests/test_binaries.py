"""Тесты скачивания ffmpeg из GUI (binaries.py + /api/binaries).

Сеть не используется: установщик подменяется заглушкой, а архив для проверки
распаковки создаётся во временном каталоге.
"""

import os
import shutil
import sys
import tempfile
import time
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flask  # noqa: E402

import binaries  # noqa: E402
import config  # noqa: E402
import models_api  # noqa: E402

EXE = binaries._exe_name('ffmpeg')
FFPROBE_EXE = binaries._exe_name('ffprobe')


class FakeInstaller:
    """Заглушка установщика: имитирует прогресс и создаёт файл бинарника."""

    def __init__(self, install_dir, supported=True, fail=None):
        self.install_dir = install_dir
        self.supported = supported
        self.fail = fail
        self.install_calls = 0

    def build_info(self):
        return {
            'supported': self.supported,
            'os': 'Windows',
            'arch': 'AMD64',
            'url': 'https://example.invalid/ffmpeg.zip',
            'archive': 'zip',
            'size_mb': 150,
            'install_dir': self.install_dir,
            'hint': None if self.supported else 'macOS: brew install ffmpeg',
        }

    def ffmpeg_version(self, path=None):
        return 'ffmpeg version test' if path and os.path.exists(str(path)) else None

    def install(self, progress=None):
        self.install_calls += 1
        if progress:
            progress(status_text='Скачивание', progress=50, downloaded_mb=10, total_mb=20)
        if self.fail:
            raise RuntimeError(self.fail)
        os.makedirs(self.install_dir, exist_ok=True)
        target = os.path.join(self.install_dir, EXE)
        with open(target, 'w', encoding='utf-8') as fh:
            fh.write('fake')
        if progress:
            progress(status_text='Готово', progress=100)
        return {'ffmpeg': target, 'ffprobe': '', 'version': 'ffmpeg version test'}


def make_client(installer, ffmpeg_path=''):
    application = flask.Flask(__name__)
    application.register_blueprint(models_api.create_blueprint(
        model_dir=tempfile.mkdtemp(),
        default_model_size='small',
        llm_model='gemma3',
        ollama_url='http://127.0.0.1:9',
        ffmpeg_path=ffmpeg_path,
        ffmpeg_installer=installer,
    ))
    return application.test_client()


def wait_for_task(client, key='ffmpeg', timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        tasks = client.get('/api/models/tasks').get_json()
        task = tasks.get(key)
        if task and task.get('status') in ('done', 'error'):
            return task
        time.sleep(0.02)
    raise AssertionError('задача не завершилась за отведённое время')


class BinariesApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.install_dir = os.path.join(self._tmp.name, 'bin')

    def tearDown(self):
        self._tmp.cleanup()

    def test_status_reports_platform_and_size(self):
        client = make_client(FakeInstaller(self.install_dir))
        data = client.get('/api/binaries/ffmpeg').get_json()
        self.assertFalse(data['ok'])
        self.assertTrue(data['download']['supported'])
        self.assertEqual(data['download']['install_dir'], self.install_dir)
        self.assertIn('Скачать', data['hint'])

    def test_setup_exposes_download_info(self):
        client = make_client(FakeInstaller(self.install_dir))
        data = client.get('/api/setup').get_json()
        self.assertFalse(data['ffmpeg']['ok'])
        self.assertTrue(data['ffmpeg']['download']['supported'])

    def test_download_runs_in_background_and_sets_path(self):
        installer = FakeInstaller(self.install_dir)
        client = make_client(installer)
        response = client.post('/api/binaries/ffmpeg/download')
        self.assertEqual(response.status_code, 200)
        task = wait_for_task(client)
        self.assertEqual(task['status'], 'done')
        self.assertEqual(task['progress'], 100)
        self.assertEqual(installer.install_calls, 1)

    def test_download_reports_install_error(self):
        client = make_client(FakeInstaller(self.install_dir, fail='Нет места на диске'))
        client.post('/api/binaries/ffmpeg/download')
        task = wait_for_task(client)
        self.assertEqual(task['status'], 'error')
        self.assertIn('Нет места', task['error'])

    def test_unsupported_platform_returns_hint(self):
        client = make_client(FakeInstaller(self.install_dir, supported=False))
        response = client.post('/api/binaries/ffmpeg/download')
        self.assertEqual(response.status_code, 400)
        self.assertIn('brew', response.get_json()['hint'])

    def test_installed_ffmpeg_is_not_downloaded_twice(self):
        os.makedirs(self.install_dir, exist_ok=True)
        binary = os.path.join(self.install_dir, EXE)
        with open(binary, 'w', encoding='utf-8') as fh:
            fh.write('fake')
        installer = FakeInstaller(self.install_dir)
        client = make_client(installer, ffmpeg_path=binary)
        response = client.post('/api/binaries/ffmpeg/download')
        self.assertTrue(response.get_json()['already'])
        self.assertEqual(installer.install_calls, 0)


class BuildInfoTests(unittest.TestCase):
    def test_known_platforms_have_archives(self):
        self.assertIn('Windows', binaries.ARCHIVES)
        self.assertIn('Linux', binaries.ARCHIVES)
        self.assertTrue(binaries.ARCHIVES['Windows']['amd64'][0].endswith('.zip'))
        self.assertTrue(binaries.ARCHIVES['Linux']['x86_64'][0].endswith('.tar.xz'))

    def test_explicit_url_overrides_platform(self):
        os.environ['FFMPEG_DOWNLOAD_URL'] = 'https://example.invalid/custom.zip'
        try:
            info = binaries.build_info()
            self.assertTrue(info['supported'])
            self.assertEqual(info['url'], 'https://example.invalid/custom.zip')
            self.assertEqual(info['archive'], 'zip')
        finally:
            del os.environ['FFMPEG_DOWNLOAD_URL']


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_bin_dir = config.BIN_DIR
        config.BIN_DIR = os.path.join(self._tmp.name, 'bin')

    def tearDown(self):
        config.BIN_DIR = self._old_bin_dir
        self._tmp.cleanup()

    def test_extracts_only_binaries_from_zip(self):
        archive = os.path.join(self._tmp.name, 'ffmpeg.zip')
        with zipfile.ZipFile(archive, 'w') as zf:
            zf.writestr('ffmpeg-7.1/bin/' + EXE, b'binary')
            zf.writestr('ffmpeg-7.1/bin/' + FFPROBE_EXE, b'binary')
            zf.writestr('ffmpeg-7.1/LICENSE.txt', b'license')
            zf.writestr('ffmpeg-7.1/bin/ffplay' + ('.exe' if os.name == 'nt' else ''), b'player')

        extracted = binaries._extract_archive(archive, 'zip')
        self.assertEqual(set(extracted), {EXE, FFPROBE_EXE})
        self.assertTrue(os.path.exists(os.path.join(config.BIN_DIR, EXE)))
        self.assertFalse(os.path.exists(os.path.join(config.BIN_DIR, 'ffplay.exe')))
        shutil.rmtree(config.BIN_DIR, ignore_errors=True)

    def test_missing_binary_in_archive_is_an_error(self):
        archive = os.path.join(self._tmp.name, 'broken.zip')
        with zipfile.ZipFile(archive, 'w') as zf:
            zf.writestr('bin/' + EXE, b'binary')
        with self.assertRaises(RuntimeError):
            binaries._extract_archive(archive, 'zip')


class ConfigResolutionTests(unittest.TestCase):
    def test_bin_dir_binary_is_preferred_over_path_lookup(self):
        tmp = tempfile.mkdtemp()
        old_bin_dir = config.BIN_DIR
        config.BIN_DIR = tmp
        try:
            binary = os.path.join(tmp, EXE)
            with open(binary, 'w', encoding='utf-8') as fh:
                fh.write('fake')
            self.assertEqual(config._resolve_binary('CUTLINE_TEST_FFMPEG_PATH', 'ffmpeg'), binary)
        finally:
            config.BIN_DIR = old_bin_dir
            shutil.rmtree(tmp, ignore_errors=True)

    def test_env_variable_wins(self):
        os.environ['CUTLINE_TEST_FFMPEG_PATH'] = '/custom/ffmpeg'
        try:
            self.assertEqual(config._resolve_binary('CUTLINE_TEST_FFMPEG_PATH', 'ffmpeg'), '/custom/ffmpeg')
        finally:
            del os.environ['CUTLINE_TEST_FFMPEG_PATH']


if __name__ == '__main__':
    unittest.main()
