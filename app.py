"""Cutline — точка входа и публичный фасад приложения.

Код разложен по модулям (без циклических импортов, порядок снизу вверх):

    config.py      — пути, переменные окружения, константы, логирование
    jobstore.py    — состояние задач, очередь, персистентность, уборка файлов
    media.py       — ffmpeg: длительность, конвертация, нарезка, скачивание
    transcribe.py  — faster-whisper, субтитры, кэш транскриптов
    summarize.py   — Ollama: сводка и главы
    pipeline.py    — полный цикл обработки задачи
    routes.py      — Flask-приложение и HTTP API

Имена реэкспортируются здесь для обратной совместимости: их используют run.py,
тесты, PyInstaller-сборка и внешние скрипты (`import app; app.main()`).
"""

import os
import threading

from config import (
    ACCESS_TOKEN,
    ALLOWED_EXTENSIONS,
    ALLOWED_FORMATS,
    ALLOWED_MODEL_SIZES,
    ALLOWED_MODES,
    APP_DIR,
    BIN_DIR,
    CACHE_FOLDER,
    CACHE_TTL_DAYS,
    DATA_DIR,
    DEBUG,
    FFMPEG_PATH,
    FFPROBE_PATH,
    HOST,
    JOBS_STORE,
    KEEP_RESULTS,
    LLM_MODEL,
    LOG_DIR,
    MAX_CONCURRENT_JOBS,
    MAX_FILES_PER_JOB,
    MAX_JOB_DETAILS,
    MAX_JOB_HISTORY,
    MAX_UPLOAD_MB,
    MAX_WORKERS,
    MODEL_DIR,
    OLLAMA_URL,
    OUTPUT_FOLDER,
    PORT,
    TEMP_FOLDER,
    TEMPLATES_DIR,
    UPLOAD_FOLDER,
    UPLOAD_TTL_HOURS,
    WHISPER_MODEL_SIZE,
    ffmpeg_path,
    logger,
    set_access_token,
)
from jobstore import (
    JobCancelled,
    _jobs_payload,
    cleanup_old_files,
    fail_job,
    finish_job,
    get_job,
    is_cancelled,
    job_slots,
    jobs,
    jobs_lock,
    load_jobs_from_disk,
    queue_gate,
    save_jobs_to_disk,
    set_job,
    update_job,
)
from media import (
    calculate_keep_segments,
    cleanup_temp,
    convert_to_format,
    download_from_url,
    get_duration,
    merge_intervals,
    parallel_media_cut,
    process_replace_chunked,
    process_single_file_to_temp,
)
from pipeline import process_task_multiple
from routes import app, build_upload_path, get_jobs_snapshot
from summarize import (
    _split_text_chunks,
    ensure_ollama_model,
    ollama_status,
    summarize_transcript,
)
from transcribe import (
    calculate_file_hash,
    create_highlight_srt,
    create_highlight_txt,
    create_srt,
    create_txt,
    format_timestamp,
    get_transcript_and_matches,
    get_whisper_model,
    normalize_text,
)

__all__ = [
    # config
    'ACCESS_TOKEN', 'ALLOWED_EXTENSIONS', 'ALLOWED_FORMATS', 'ALLOWED_MODES', 'ALLOWED_MODEL_SIZES',
    'APP_DIR', 'BIN_DIR', 'CACHE_FOLDER', 'CACHE_TTL_DAYS', 'DATA_DIR', 'DEBUG', 'FFMPEG_PATH',
    'FFPROBE_PATH',
    'HOST', 'JOBS_STORE', 'KEEP_RESULTS', 'LLM_MODEL', 'LOG_DIR', 'MAX_CONCURRENT_JOBS',
    'MAX_FILES_PER_JOB', 'MAX_JOB_DETAILS', 'MAX_JOB_HISTORY', 'MAX_UPLOAD_MB', 'MAX_WORKERS',
    'MODEL_DIR', 'OLLAMA_URL', 'OUTPUT_FOLDER', 'PORT', 'TEMPLATES_DIR', 'TEMP_FOLDER',
    'UPLOAD_FOLDER', 'UPLOAD_TTL_HOURS', 'WHISPER_MODEL_SIZE', 'logger', 'set_access_token',
    # jobstore
    'JobCancelled', '_jobs_payload', 'cleanup_old_files', 'fail_job', 'finish_job', 'get_job',
    'is_cancelled', 'job_slots', 'jobs', 'jobs_lock', 'load_jobs_from_disk', 'queue_gate',
    'save_jobs_to_disk', 'set_job', 'update_job',
    # media
    'calculate_keep_segments', 'cleanup_temp', 'convert_to_format', 'download_from_url', 'get_duration',
    'merge_intervals', 'parallel_media_cut', 'process_replace_chunked', 'process_single_file_to_temp',
    # transcribe
    'calculate_file_hash', 'create_highlight_srt', 'create_highlight_txt', 'create_srt', 'create_txt',
    'format_timestamp', 'get_transcript_and_matches', 'get_whisper_model', 'normalize_text',
    # summarize
    '_split_text_chunks', 'ensure_ollama_model', 'ollama_status', 'summarize_transcript',
    # pipeline / routes
    'process_task_multiple', 'app', 'build_upload_path', 'get_jobs_snapshot', 'main',
]


def main():
    """Запуск сервера: используется и в dev-режиме, и в собранном exe (run.py)."""
    load_jobs_from_disk()
    cleanup_old_files()
    logger.info(f"Cutline запущен: http://127.0.0.1:{PORT} (host={HOST}, debug={DEBUG})")
    logger.info(f"ffmpeg: {ffmpeg_path()} | Ollama: {OLLAMA_URL} | Whisper: {WHISPER_MODEL_SIZE}")
    if HOST not in ('127.0.0.1', 'localhost') and not ACCESS_TOKEN:
        logger.warning(f"Сервер слушает {HOST} без ACCESS_TOKEN: доступ открыт всей локальной сети")
    if os.environ.get('OPEN_BROWSER', '0') == '1':
        import webbrowser
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    # use_reloader=False: иначе запускаются два процесса и модель грузится дважды
    if DEBUG or os.environ.get('USE_WAITRESS', '1') == '0':
        app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True, use_reloader=False)
    else:
        try:
            from waitress import serve
        except ImportError:
            app.run(host=HOST, port=PORT, threaded=True, use_reloader=False)
        else:
            # waitress: стабильный WSGI-сервер вместо dev-сервера Flask
            serve(app, host=HOST, port=PORT, threads=max(8, MAX_CONCURRENT_JOBS * 4),
                  channel_timeout=3600)


if __name__ == '__main__':
    main()
