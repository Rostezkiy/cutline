"""Состояние задач, очередь, персистентность и уборка файлов."""

import json
import os
import threading
import time

from config import CACHE_FOLDER, CACHE_TTL_DAYS, JOBS_STORE, KEEP_RESULTS, MAX_CONCURRENT_JOBS, MAX_JOB_DETAILS, MAX_JOB_HISTORY, OUTPUT_FOLDER, UPLOAD_FOLDER, UPLOAD_TTL_HOURS, logger


# --- СОСТОЯНИЕ И ОЧЕРЕДЬ ---
jobs = {}
jobs_lock = threading.Lock()  # Защита словаря jobs от гонок между потоками
job_slots = threading.BoundedSemaphore(MAX_CONCURRENT_JOBS)  # Очередь: не более N параллельных задач
# Пауза очереди: set() - работаем, clear() - новые задачи ждут (см. /api/queue)
queue_gate = threading.Event()
queue_gate.set()


def _wait_while_paused(task_id):
    """Ждёт снятия паузы очереди, продолжая реагировать на отмену задачи."""
    while not queue_gate.is_set():
        if is_cancelled(task_id):
            fail_job(task_id, 'Отменено пользователем', cancelled=True)
            return False
        queue_gate.wait(0.5)
    return True


class JobCancelled(Exception):
    """Внутреннее исключение для отмены задачи пользователем."""
    pass


# --- JOBS: доступ, персистентность, отмена ---
def get_job(task_id):
    with jobs_lock:
        return jobs.get(task_id)


def _prune_jobs_locked():
    """Ограничивает историю: самые старые завершённые задачи удаляются."""
    if len(jobs) <= MAX_JOB_HISTORY:
        return
    finished = sorted(
        ((tid, job) for tid, job in jobs.items()
         if job.get('status') in ('completed', 'error', 'cancelled')),
        key=lambda kv: kv[1].get('finished_at') or kv[1].get('created_at') or 0,
    )
    for tid, _ in finished[:max(0, len(jobs) - MAX_JOB_HISTORY)]:
        jobs.pop(tid, None)


def set_job(task_id, data):
    with jobs_lock:
        jobs[task_id] = data
        _prune_jobs_locked()


def update_job(task_id, status, percent, **kwargs):
    with jobs_lock:
        if task_id in jobs:
            jobs[task_id]['status'] = status
            jobs[task_id]['percent'] = percent
            for k, v in kwargs.items():
                jobs[task_id][k] = v


def is_cancelled(task_id):
    job = get_job(task_id)
    return bool(job and job.get('cancel'))


def _jobs_payload():
    """Снимок задач для диска.

    Тяжёлые поля (matches_list/full_transcript) сохраняем только для последних
    MAX_JOB_DETAILS задач - иначе history-файл разрастается до сотен МБ.
    """
    with jobs_lock:
        ordered = sorted(
            jobs.items(),
            key=lambda kv: kv[1].get('finished_at') or kv[1].get('created_at') or 0,
            reverse=True,
        )
        payload = {}
        for index, (tid, job) in enumerate(ordered):
            item = dict(job)
            if index >= MAX_JOB_DETAILS:
                item.pop('matches_list', None)
                item.pop('full_transcript', None)
            payload[tid] = item
    return payload


def save_jobs_to_disk():
    """Атомарно сохраняет словарь задач в JSON (история переживает рестарт)."""
    try:
        snapshot = json.dumps(_jobs_payload(), ensure_ascii=False, default=str)
        tmp = JOBS_STORE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(snapshot)
        os.replace(tmp, JOBS_STORE)
    except Exception as e:
        logger.error(f"Failed to save jobs store: {e}")


def load_jobs_from_disk():
    if not os.path.exists(JOBS_STORE):
        return
    try:
        with open(JOBS_STORE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        with jobs_lock:
            for tid, job in data.items():
                # Незавершённые задачи с прошлого запуска помечаем как прерванные
                if job.get('status') not in ('completed', 'error', 'cancelled'):
                    job['status'] = 'cancelled'
                    job['error'] = 'Прервано перезапуском сервера'
                jobs[tid] = job
        logger.info(f"Loaded {len(data)} jobs from {JOBS_STORE}")
    except Exception as e:
        logger.error(f"Failed to load jobs store: {e}")


def finish_job(task_id, **fields):
    """Помечает задачу завершённой, сохраняет метаданные и пишет на диск."""
    job = get_job(task_id) or {}
    job.update(fields)
    job['status'] = 'completed'
    job['percent'] = 100
    job['finished_at'] = time.time()
    set_job(task_id, job)
    save_jobs_to_disk()


def fail_job(task_id, error, cancelled=False):
    job = get_job(task_id) or {}
    job['status'] = 'cancelled' if cancelled else 'error'
    job['error'] = error
    job['percent'] = job.get('percent', 0)
    job['finished_at'] = time.time()
    set_job(task_id, job)
    save_jobs_to_disk()


def cleanup_old_files():
    """Удаляет старые uploads и лишние результаты, чтобы папки не разрастались."""
    cutoff = time.time() - UPLOAD_TTL_HOURS * 3600
    removed = 0
    try:
        for fname in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, fname)
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
                removed += 1
    except OSError as e:
        logger.error(f"Upload cleanup error: {e}")

    try:
        files = []
        for fname in os.listdir(OUTPUT_FOLDER):
            path = os.path.join(OUTPUT_FOLDER, fname)
            if fname == 'jobs_store.json' or not os.path.isfile(path):
                continue
            files.append((os.path.getmtime(path), path))
        files.sort()
        # KEEP_RESULTS=0 корректно удаляет всё (срез [:-0] раньше был пустым)
        drop_count = max(0, len(files) - max(0, KEEP_RESULTS))
        for _, path in files[:drop_count]:
            try:
                os.remove(path)
            except OSError as e:
                logger.warning(f"Cannot remove {path}: {e}")
    except OSError as e:
        logger.error(f"Results cleanup error: {e}")

    # Кэш транскриптов тоже не должен расти бесконечно
    cache_cutoff = time.time() - CACHE_TTL_DAYS * 86400
    try:
        for fname in os.listdir(CACHE_FOLDER):
            path = os.path.join(CACHE_FOLDER, fname)
            if os.path.isfile(path) and os.path.getmtime(path) < cache_cutoff:
                os.remove(path)
    except OSError as e:
        logger.warning(f"Cache cleanup error: {e}")
    logger.info(f"Cleanup done: {removed} uploads removed")
