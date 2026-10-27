"""Базовые тесты чистой логики Cutline (без ffmpeg/Whisper/Ollama).

Запуск: python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # noqa: E402


class TimestampTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(app.format_timestamp(0), "00:00:00,000")

    def test_rounding_does_not_produce_1000_ms(self):
        # 59.9999 секунды раньше давало "00:00:59,999", а 3599.9999 - сутки в минус
        self.assertEqual(app.format_timestamp(59.9999), "00:01:00,000")

    def test_hours(self):
        self.assertEqual(app.format_timestamp(3661.5), "01:01:01,500")

    def test_negative_is_clamped(self):
        self.assertEqual(app.format_timestamp(-3), "00:00:00,000")


class NormalizeTests(unittest.TestCase):
    def test_strips_punctuation_and_lowercases(self):
        self.assertEqual(app.normalize_text("Привет, МИР!"), "привет мир")

    def test_keeps_digits(self):
        self.assertEqual(app.normalize_text("Год 2024"), "год 2024")


class MergeIntervalsTests(unittest.TestCase):
    def test_merges_overlaps(self):
        merged = app.merge_intervals([
            {"start": 1.0, "end": 2.0},
            {"start": 1.5, "end": 3.0},
            {"start": 5.0, "end": 6.0},
        ])
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["end"], 3.0)

    def test_input_not_mutated(self):
        data = [{"start": 1.0, "end": 2.0}, {"start": 1.5, "end": 3.0}]
        app.merge_intervals(data)
        self.assertEqual(data[1]["end"], 3.0)

    def test_unsorted_input(self):
        merged = app.merge_intervals([{"start": 5.0, "end": 6.0}, {"start": 1.0, "end": 2.0}])
        self.assertEqual([m["start"] for m in merged], [1.0, 5.0])


class KeepSegmentsTests(unittest.TestCase):
    def test_remove_mode_returns_complement(self):
        segments = app.calculate_keep_segments([{"start": 2.0, "end": 3.0}], 10.0, "remove")
        self.assertEqual(segments, [(0.0, 2.0), (3.0, 10.0)])

    def test_save_mode_returns_matches(self):
        segments = app.calculate_keep_segments([{"start": 2.0, "end": 3.0}], 10.0, "save")
        self.assertEqual(segments, [(2.0, 3.0)])

    def test_tiny_segments_filtered(self):
        segments = app.calculate_keep_segments([{"start": 0.0, "end": 0.05}], 10.0, "remove")
        self.assertEqual(segments, [(0.05, 10.0)])


class ChunkingTests(unittest.TestCase):
    def test_short_text_single_chunk(self):
        self.assertEqual(app._split_text_chunks("Привет.", 100), ["Привет."])

    def test_splits_by_sentence_end(self):
        text = "Первое предложение. Второе предложение. Третье предложение."
        chunks = app._split_text_chunks(text, 10)  # 40 символов в чанке
        self.assertGreater(len(chunks), 1)
        self.assertEqual(" ".join(chunks), text)

    def test_empty_text(self):
        self.assertEqual(app._split_text_chunks("", 10), [])


class UploadPathTests(unittest.TestCase):
    def test_cyrillic_filename_keeps_extension(self):
        # Регрессия: secure_filename("запись.mp3") -> "mp3", файл отбрасывался
        display, path = app.build_upload_path("task1", 0, "запись с матом.mp3")
        self.assertEqual(display, "запись с матом.mp3")
        self.assertTrue(path.endswith(".mp3"))

    def test_traversal_is_stripped(self):
        display, path = app.build_upload_path("task1", 0, "../../etc/passwd.mp3")
        self.assertEqual(display, "passwd.mp3")
        self.assertNotIn("..", os.path.normpath(path).replace(os.path.dirname(app.UPLOAD_FOLDER), ""))

    def test_unsupported_extension_rejected(self):
        self.assertEqual(app.build_upload_path("t", 0, "virus.exe"), (None, None))

    def test_windows_path_uses_basename(self):
        display, _ = app.build_upload_path("t", 0, r"C:\Users\me\audio.mp3")
        self.assertEqual(display, "audio.mp3")


class JobsPayloadTests(unittest.TestCase):
    def test_heavy_fields_dropped_for_old_jobs(self):
        app.jobs.clear()
        for i in range(app.MAX_JOB_DETAILS + 3):
            app.jobs["j%d" % i] = {
                "status": "completed",
                "finished_at": i,
                "matches_list": [{"word": "x"}],
                "full_transcript": [{"text": "y"}],
            }
        payload = app._jobs_payload()
        self.assertEqual(len(payload), app.MAX_JOB_DETAILS + 3)
        newest = payload["j%d" % (app.MAX_JOB_DETAILS + 2)]
        oldest = payload["j0"]
        self.assertIn("matches_list", newest)
        self.assertNotIn("matches_list", oldest)
        app.jobs.clear()


class HealthRouteTests(unittest.TestCase):
    def test_health_returns_json(self):
        client = app.app.test_client()
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")
        for key in ("ollama", "ffmpeg", "whisper_model", "device", "active_jobs"):
            self.assertIn(key, data)


if __name__ == "__main__":
    unittest.main()
