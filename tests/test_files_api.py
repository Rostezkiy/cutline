"""Тесты пресетов в файлах и ZIP-экспорта (files_api).

Запуск: python -m unittest discover -s tests -v
"""

import json
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flask  # noqa: E402

import files_api  # noqa: E402


class FilesApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.output_dir = os.path.join(self._tmp.name, 'processed')
        os.makedirs(self.output_dir, exist_ok=True)
        self.presets_path = os.path.join(self._tmp.name, 'presets.json')
        self.jobs = {}
        application = flask.Flask(__name__)
        application.register_blueprint(files_api.create_blueprint(
            output_dir=self.output_dir,
            presets_path=self.presets_path,
            job_provider=lambda task_id: self.jobs.get(task_id),
        ))
        self.client = application.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    # --- пресеты ---

    def test_empty_presets(self):
        data = self.client.get('/api/presets').get_json()
        self.assertEqual(data['presets'], {})
        self.assertEqual(data['count'], 0)

    def test_save_and_list_preset(self):
        response = self.client.post('/api/presets', json={
            'name': 'Мат-фильтр',
            'entry': {'words': ['мат', 'блин'], 'settings': {'mode': 'replace', 'padding': 120, 'bogus': 1}},
        })
        self.assertEqual(response.status_code, 200)
        presets = self.client.get('/api/presets').get_json()['presets']
        self.assertIn('Мат-фильтр', presets)
        self.assertEqual(presets['Мат-фильтр']['words'], ['мат', 'блин'])
        self.assertEqual(presets['Мат-фильтр']['settings']['padding'], 120)
        # неизвестные ключи настроек отбрасываются
        self.assertNotIn('bogus', presets['Мат-фильтр']['settings'])
        # файл действительно создан
        self.assertTrue(os.path.isfile(self.presets_path))

    def test_save_preset_requires_words(self):
        response = self.client.post('/api/presets', json={'name': 'p', 'entry': {'words': []}})
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/presets', json={'name': '   ', 'entry': {'words': ['a']}})
        self.assertEqual(response.status_code, 400)

    def test_delete_preset(self):
        self.client.post('/api/presets', json={'name': 'p1', 'entry': {'words': ['a']}})
        self.assertEqual(self.client.delete('/api/presets/p1').status_code, 200)
        self.assertEqual(self.client.get('/api/presets').get_json()['presets'], {})
        self.assertEqual(self.client.delete('/api/presets/p1').status_code, 404)

    def test_export_and_import(self):
        self.client.post('/api/presets', json={'name': 'p1', 'entry': {'words': ['a', 'b']}})
        response = self.client.get('/api/presets/export')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response.headers['Content-Disposition'])
        exported = json.loads(response.get_data(as_text=True))
        self.assertIn('p1', exported['presets'])

        response = self.client.post('/api/presets/import', json=exported)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['imported'], 1)

    def test_import_rejects_garbage(self):
        response = self.client.post('/api/presets/import', json={'presets': 'nope'})
        self.assertEqual(response.status_code, 400)

    def test_corrupted_presets_file_is_tolerated(self):
        with open(self.presets_path, 'w', encoding='utf-8') as fh:
            fh.write('{not json')
        data = self.client.get('/api/presets').get_json()
        self.assertEqual(data['presets'], {})

    # --- ZIP ---

    def _make_job(self, task_id='t1'):
        names = {
            'media': f'{task_id}_audio.mp3',
            'srt': f'{task_id}_audio.srt',
            'txt': f'{task_id}_audio.txt',
        }
        for name in names.values():
            with open(os.path.join(self.output_dir, name), 'wb') as fh:
                fh.write(b'data')
        self.jobs[task_id] = {
            'status': 'completed',
            'mode': 'replace',
            'filenames': ['audio.mp3'],
            'match_count': 2,
            'download_url': f"/download/{names['media']}",
            'srt_url': f"/download/{names['srt']}",
            'txt_url': f"/download/{names['txt']}",
        }

    def test_export_zip_contains_files(self):
        self._make_job()
        response = self.client.get('/api/export/t1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/zip')
        archive_path = os.path.join(self._tmp.name, 'out.zip')
        with open(archive_path, 'wb') as fh:
            fh.write(response.get_data())
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            self.assertIn('t1_audio.mp3', names)
            self.assertIn('t1_audio.srt', names)
            self.assertIn('report.json', names)
            self.assertIn('README.txt', names)
            report = json.loads(archive.read('report.json').decode('utf-8'))
            self.assertEqual(report['match_count'], 2)

    def test_export_zip_unknown_task(self):
        self.assertEqual(self.client.get('/api/export/missing').status_code, 404)

    def test_export_zip_unfinished_task(self):
        self.jobs['t2'] = {'status': 'queued'}
        self.assertEqual(self.client.get('/api/export/t2').status_code, 400)

    def test_export_zip_without_files(self):
        self.jobs['t3'] = {'status': 'completed', 'download_url': '/download/none.mp3'}
        self.assertEqual(self.client.get('/api/export/t3').status_code, 404)


if __name__ == '__main__':
    unittest.main()
