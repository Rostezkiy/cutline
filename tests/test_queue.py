"""Тесты очереди задач: пауза/продолжение и отмена задачи в очереди.

Запуск: python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # noqa: E402


class QueueRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        app.queue_gate.set()

    def tearDown(self):
        app.queue_gate.set()

    def test_queue_status_structure(self):
        data = self.client.get('/api/queue').get_json()
        for key in ('paused', 'active', 'queued', 'max_concurrent_jobs'):
            self.assertIn(key, data)
        self.assertFalse(data['paused'])

    def test_pause_and_resume(self):
        self.assertTrue(self.client.post('/api/queue/pause').get_json()['paused'])
        self.assertFalse(app.queue_gate.is_set())
        self.assertTrue(self.client.get('/api/queue').get_json()['paused'])
        self.assertFalse(self.client.post('/api/queue/resume').get_json()['paused'])
        self.assertTrue(app.queue_gate.is_set())

    def test_cancel_queued_job_marks_cancelled(self):
        task_id = 'test-queued-cancel'
        app.set_job(task_id, {'status': 'queued', 'percent': 0, 'cancel': False, 'created_at': 0})
        response = self.client.post(f'/cancel/{task_id}')
        self.assertEqual(response.status_code, 200)
        job = app.get_job(task_id)
        self.assertEqual(job['status'], 'cancelled')
        self.assertTrue(job['cancel'])
        with app.jobs_lock:
            app.jobs.pop(task_id, None)

    def test_cancel_unknown_job(self):
        self.assertEqual(self.client.post('/cancel/no-such-task').status_code, 404)


if __name__ == '__main__':
    unittest.main()
