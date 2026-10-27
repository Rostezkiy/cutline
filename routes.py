"""Flask-приложение, HTTP API и обработчики маршрутов."""

import os
import re
import threading
import time
import uuid

from flask import Flask, g, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

import config
import runtime_settings
import transcribe
from config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_FORMATS,
    ALLOWED_MODEL_SIZES,
    ALLOWED_MODES,
    CACHE_FOLDER,
    DATA_DIR,
    LLM_MODEL,
    MAX_CONCURRENT_JOBS,
    MAX_FILES_PER_JOB,
    MAX_UPLOAD_MB,
    MODEL_DIR,
    OLLAMA_URL,
    OUTPUT_FOLDER,
    TEMP_FOLDER,
    TEMPLATES_DIR,
    UPLOAD_FOLDER,
    WHISPER_MODEL_SIZE,
    logger,
)
from jobstore import cleanup_old_files, get_job, jobs, jobs_lock, queue_gate, set_job
from media import download_from_url
from pipeline import process_task_multiple
from summarize import ollama_status
from transcribe import _model_cache, device_info, normalize_text

# --- ПРИЛОЖЕНИЕ ---
app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['TEMP_FOLDER'] = TEMP_FOLDER
app.config['CACHE_FOLDER'] = CACHE_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024


@app.before_request
def _check_access_token():
    if not config.ACCESS_TOKEN:
        return None
    token = (request.headers.get('X-Access-Token') or request.args.get('token')
             or request.cookies.get('cutline_token') or '')
    if token != config.ACCESS_TOKEN:
        return jsonify({'error': 'Требуется токен доступа (ACCESS_TOKEN)'}), 401
    if request.args.get('token'):
        g.set_token_cookie = True
    return None


@app.after_request
def _set_token_cookie(response):
    if config.ACCESS_TOKEN and getattr(g, 'set_token_cookie', False):
        response.set_cookie('cutline_token', config.ACCESS_TOKEN, httponly=True, samesite='Lax')
    return response


# --- МОДЕЛИ И ПЕРВИЧНАЯ НАСТРОЙКА (Blueprint, см. models_api.py) ---
# Импорт после конфигурации: модуль не зависит от app.py (без циклического импорта).
import binaries  # noqa: E402
import models_api  # noqa: E402

app.register_blueprint(models_api.create_blueprint(
    model_dir=MODEL_DIR,
    default_model_size=WHISPER_MODEL_SIZE,
    llm_model=LLM_MODEL,
    ollama_url=OLLAMA_URL,
    allowed_sizes=ALLOWED_MODEL_SIZES,
    ffmpeg_path=config.ffmpeg_path,  # провайдер: путь меняется после скачивания из GUI
    ffmpeg_installer=binaries,
    binary_refresh=config.refresh_binary_paths,
    logger=logger,
    device_provider=device_info,
    active_model_getter=runtime_settings.get_llm_model,
    active_model_setter=runtime_settings.set_llm_model,
))

# --- ПРЕСЕТЫ И ZIP-ЭКСПОРТ (Blueprint, см. files_api.py) ---
import files_api  # noqa: E402

app.register_blueprint(files_api.create_blueprint(
    output_dir=OUTPUT_FOLDER,
    presets_path=os.path.join(DATA_DIR, 'presets.json'),
    job_provider=lambda task_id: get_job(task_id),
    logger=logger,
))


# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    """Статус сервиса: доступность Ollama и загруженные модели."""
    ollama_ok, ollama_models = ollama_status()
    active_model = runtime_settings.get_llm_model()
    ffmpeg_ok = config.binary_exists(config.ffmpeg_path())
    return jsonify({
        'status': 'ok',
        'ollama': ollama_ok,
        'ollama_models': ollama_models,
        'llm_model': active_model,
        'llm_model_ready': any(m == active_model or m.split(':')[0] == active_model.split(':')[0]
                                for m in ollama_models),
        'whisper_model': WHISPER_MODEL_SIZE,
        'whisper_loaded': sorted(_model_cache.keys()),
        'whisper_error': transcribe.model_error,
        'device': device_info()[0],
        'compute_type': device_info()[1],
        'ffmpeg': ffmpeg_ok,
        'max_concurrent_jobs': MAX_CONCURRENT_JOBS,
        'active_jobs': sum(1 for j in get_jobs_snapshot().values()
                           if j.get('status') not in ('completed', 'error', 'cancelled'))
    })


@app.route('/download/<filename>')
def download_file(filename):
    response = send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route('/media/<filename>')
def media_file(filename):
    """Отдаёт файл инлайн для проигрывания в браузере (плееру нужен inline, не attachment)."""
    response = send_from_directory(OUTPUT_FOLDER, filename)
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route('/report/<task_id>')
def job_report(task_id):
    """Экспорт отчёта задачи в JSON (метаданные, совпадения, статистика)."""
    job = get_job(task_id)
    if not job:
        return jsonify({'error': 'Not found'}), 404
    if job.get('status') != 'completed':
        return jsonify({'error': 'Задача не завершена'}), 400
    report = {
        'task_id': task_id,
        'created_at': job.get('created_at'),
        'finished_at': job.get('finished_at'),
        'mode': job.get('mode'),
        'filenames': job.get('filenames'),
        'words': job.get('words'),
        'match_count': job.get('match_count'),
        'word_counts': job.get('word_counts'),
        'matches': job.get('matches_list'),
        'output': job.get('filename'),
        'download_url': job.get('download_url'),
        'srt_url': job.get('srt_url'),
        'txt_url': job.get('txt_url'),
    }
    resp = jsonify(report)
    resp.headers['Content-Disposition'] = f'attachment; filename=report_{task_id}.json'
    return resp

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Статика фронтенда (css/js) из templates/ - без перехвата остальных роутов."""
    if filename.endswith(('.css', '.js')):
        return send_from_directory(TEMPLATES_DIR, filename)
    return "Not Found", 404


@app.errorhandler(413)
def too_large(_error):
    return jsonify({'error': f'Файл слишком большой (лимит {MAX_UPLOAD_MB} МБ)'}), 413


def get_jobs_snapshot():
    with jobs_lock:
        return dict(jobs)


@app.route('/status/<task_id>')
def job_status(task_id):
    return jsonify(get_job(task_id) or {'status': 'unknown'})


@app.route('/results/<task_id>')
def get_result(task_id):
    job = get_job(task_id)
    if not job:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(job)


@app.route('/history')
def history():
    """История завершённых задач (для вкладки Results после рестарта)."""
    items = []
    with jobs_lock:
        for tid, job in jobs.items():
            if job.get('status') in ('completed', 'error', 'cancelled'):
                # Лёгкая выдача: без массивов совпадений/транскрипта (они - в /results).
                items.append({
                    'task_id': tid,
                    'status': job.get('status'),
                    'mode': job.get('mode'),
                    'filenames': job.get('filenames'),
                    'filename': job.get('filename'),
                    'created_at': job.get('created_at'),
                    'finished_at': job.get('finished_at'),
                    'match_count': job.get('match_count'),
                    'download_url': job.get('download_url'),
                    'error': job.get('error'),
                })
    items.sort(key=lambda x: x.get('finished_at', 0), reverse=True)
    return jsonify(items[:50])


@app.route('/cancel/<task_id>', methods=['POST'])
def cancel_job(task_id):
    job = get_job(task_id)
    if not job:
        return jsonify({'error': 'Задача не найдена'}), 404
    if job.get('status') in ('completed', 'error', 'cancelled'):
        return jsonify({'error': 'Задача уже завершена'}), 400
    with jobs_lock:
        job['cancel'] = True
        # Задача ещё в очереди - снимаем её сразу, не дожидаясь слота
        if job.get('status') == 'queued':
            job['status'] = 'cancelled'
            job['finished_at'] = time.time()
            job['error'] = 'Отменено пользователем'
    return jsonify({'success': True})


@app.route('/api/queue')
def queue_status():
    """Состояние очереди: пауза, активные и ожидающие задачи."""
    snapshot = get_jobs_snapshot()
    done_states = ('completed', 'error', 'cancelled', 'queued')
    active = [tid for tid, job in snapshot.items() if job.get('status') not in done_states]
    queued = [tid for tid, job in snapshot.items() if job.get('status') == 'queued']
    return jsonify({
        'paused': not queue_gate.is_set(),
        'active': len(active),
        'queued': len(queued),
        'max_concurrent_jobs': MAX_CONCURRENT_JOBS,
    })


@app.route('/api/queue/pause', methods=['POST'])
def queue_pause():
    queue_gate.clear()
    logger.info('Очередь на паузе')
    return jsonify({'success': True, 'paused': True})


@app.route('/api/queue/resume', methods=['POST'])
def queue_resume_all():
    queue_gate.set()
    logger.info('Очередь продолжена')
    return jsonify({'success': True, 'paused': False})


def build_upload_path(task_id, index, original_name):
    """Возвращает (имя_для_отображения, путь_на_диске) или (None, None).

    secure_filename() выбрасывает не-ASCII ("запись.mp3" -> "mp3"), из-за чего
    такие файлы раньше молча отбрасывались. Теперь расширение берём из
    оригинального имени, а на диске используем безопасный ASCII-идентификатор.
    """
    display_name = os.path.basename((original_name or '').replace('\\', '/')).strip()
    ext = os.path.splitext(display_name)[1].lower()
    if not display_name or ext not in ALLOWED_EXTENSIONS:
        return None, None
    safe_stem = secure_filename(os.path.splitext(display_name)[0])[:60] or 'file'
    path = os.path.join(UPLOAD_FOLDER, f"{task_id}_{index}_{safe_stem}{ext}")
    return display_name, path


@app.route('/process', methods=['POST'])
def handle_process():
    files = request.files.getlist('file')
    url = (request.form.get('url') or '').strip()
    if (not files or files[0].filename == '') and not url:
        return jsonify({'error': 'Файл не выбран'}), 400

    try:
        settings = {
            'padding': int(request.form.get('padding', 0)),
            'format': request.form.get('format', 'mp3'),
            'beep_freq': int(request.form.get('beep_freq', 1000)),
            'beep_gain': int(request.form.get('beep_gain', -10)),
            'mute': request.form.get('mute', '') == '1',
            'stem_match': request.form.get('stem_match', '') == '1',
            'accurate_cut': request.form.get('accurate_cut', '1') == '1',
            'language': (request.form.get('language', '') or '').strip().lower() or None,
            'model_size': (request.form.get('model_size', '') or '').strip() or WHISPER_MODEL_SIZE,
        }
    except ValueError:
        return jsonify({'error': 'Некорректные параметры настроек'}), 400

    # Границы значений - защита от бессмысленных/опасных настроек
    settings['padding'] = max(0, min(2000, settings['padding']))
    settings['beep_freq'] = max(100, min(5000, settings['beep_freq']))
    settings['beep_gain'] = max(-40, min(0, settings['beep_gain']))

    if settings['format'] not in ALLOWED_FORMATS:
        return jsonify({'error': 'Неподдерживаемый формат вывода'}), 400
    if settings['model_size'] not in ALLOWED_MODEL_SIZES:
        return jsonify({'error': 'Неподдерживаемый размер модели Whisper'}), 400
    if settings['language'] and not re.fullmatch(r'[a-z]{2,5}', settings['language']):
        return jsonify({'error': 'Некорректный код языка (например: ru, en, auto)'}), 400

    # Обработка слов
    raw_words = request.form.get('words', '')
    words = raw_words.split(',')
    words = [normalize_text(w) for w in words if w.strip()]

    # Обработка mode (дефолт remove)
    mode = request.form.get('mode', 'remove')
    if mode not in ALLOWED_MODES:
        return jsonify({'error': 'Неизвестный режим обработки'}), 400
    if mode != 'summarize' and not words:
        return jsonify({'error': 'Список слов пуст'}), 400

    task_id = str(uuid.uuid4())

    # Очистка старых файлов перед новой загрузкой
    cleanup_old_files()

    # Сохраняем файлы (с валидацией расширений)
    input_paths = []
    filenames = []
    for i, file in enumerate(files):
        if not file or not file.filename:
            continue
        if len(input_paths) >= MAX_FILES_PER_JOB:
            logger.warning(f"Слишком много файлов, лимит {MAX_FILES_PER_JOB}")
            break
        display_name, input_path = build_upload_path(task_id, i, file.filename)
        if not input_path:
            logger.warning(f"Skipping unsupported file: {file.filename}")
            continue
        file.save(input_path)
        input_paths.append(input_path)
        filenames.append(display_name)

    # Если файлов нет, но указана ссылка - скачиваем (например, YouTube)
    if not input_paths and url:
        try:
            dl_path, dl_title = download_from_url(url, UPLOAD_FOLDER)
            input_paths.append(dl_path)
            filenames.append(secure_filename(os.path.basename(dl_path)) or f"url_{task_id[:8]}.mp3")
            logger.info(f"Downloaded from URL: {dl_title} -> {dl_path}")
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 400

    # Если файлов нет (все пустые / не поддерживаются)
    if not input_paths:
        return jsonify({'error': 'Нет подходящих файлов (поддерживаются: аудио/видео распространённых форматов)'}), 400

    # Регистрируем задачу ДО запуска потока (иначе первые update_job теряются)
    set_job(task_id, {
        'status': 'queued',
        'percent': 0,
        'created_at': time.time(),
        'filenames': filenames,
        'mode': mode,
        'words': words,
        'cancel': False,
    })

    # Запускаем задачу обработки
    thread = threading.Thread(target=process_task_multiple, args=(task_id, input_paths, filenames, words, mode, settings))
    thread.daemon = True
    thread.start()
    return jsonify({'success': True, 'task_id': task_id})
