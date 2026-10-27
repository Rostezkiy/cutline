"""Каталог моделей и первичная настройка Cutline.

Модуль намеренно не импортирует app.py: при запуске `python app.py` главный модуль
называется `__main__`, и `import app` создал бы вторую копию приложения (со своими
очередями задач). Все зависимости передаются через create_blueprint().

Роуты (префикс /api):
    GET  /api/setup                  - отчёт о готовности окружения (ffmpeg, модели, Ollama)
    GET  /api/models                 - каталог моделей (Whisper + Ollama) и локальные модели
    POST /api/models/whisper/download - скачивание модели Whisper с HuggingFace
    POST /api/models/ollama/pull     - скачивание модели Ollama по имени (стрим с прогрессом)
    POST /api/models/ollama/import   - импорт GGUF-файла по прямой ссылке (`ollama create`)
    POST /api/models/ollama/active   - выбор LLM-модели для сводок (сохраняется в настройках)
    POST /api/ollama/start           - автозапуск `ollama serve`
    GET  /api/models/tasks           - прогресс активных скачиваний (модели и ffmpeg)
    GET  /api/binaries/ffmpeg        - статус ffmpeg и возможность скачать его из GUI
    POST /api/binaries/ffmpeg/download - скачивание ffmpeg/ffprobe в каталог данных
"""

import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time

import requests
from flask import Blueprint, jsonify, request

# Каталог моделей Whisper: размер -> репозиторий и оценка ресурсов.
# size_mb используется для прогресса скачивания и подсказок по диску.
WHISPER_CATALOG = {
    'tiny': {'repo': 'Systran/faster-whisper-tiny', 'size_mb': 75, 'ram_gb': 2, 'quality': 1, 'note': 'Черновик, очень быстро'},
    'base': {'repo': 'Systran/faster-whisper-base', 'size_mb': 145, 'ram_gb': 3, 'quality': 2, 'note': 'Быстро, качество ниже среднего'},
    'small': {'repo': 'Systran/faster-whisper-small', 'size_mb': 484, 'ram_gb': 4, 'quality': 3, 'note': 'Баланс для слабых ПК и CPU'},
    'medium': {'repo': 'Systran/faster-whisper-medium', 'size_mb': 1536, 'ram_gb': 6, 'quality': 4, 'note': 'Рекомендуется по умолчанию'},
    'large': {'repo': 'Systran/faster-whisper-large-v3', 'size_mb': 3090, 'ram_gb': 10, 'quality': 5, 'note': 'Максимальное качество (large-v3)'},
    'large-v3': {'repo': 'Systran/faster-whisper-large-v3', 'size_mb': 3090, 'ram_gb': 10, 'quality': 5, 'note': 'Максимальное качество'},
}

# Модели Ollama, которые предлагаем для сводок (первая - рекомендованная).
OLLAMA_CATALOG = [
    {'name': 'gemma3:4b', 'size_mb': 3300, 'note': 'Быстрая сводка, 8 ГБ RAM'},
    {'name': 'llama3.2:3b', 'size_mb': 2000, 'note': 'Очень быстрая, 6 ГБ RAM'},
    {'name': 'qwen2.5:7b', 'size_mb': 4700, 'note': 'Хорошо для русского, 12 ГБ RAM'},
    {'name': 'mistral:7b', 'size_mb': 4400, 'note': 'Универсальная, 12 ГБ RAM'},
]

WHISPER_MODEL_FILES = ('model.bin', 'config.json')
# Имя модели Ollama: только безопасные символы (никаких пробелов и путей).
_MODEL_NAME_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}')


def _find_ollama_binary():
    """Путь к исполняемому файлу Ollama (если установлен)."""
    found = shutil.which('ollama')
    if found:
        return found
    candidates = []
    if os.name == 'nt':
        local = os.environ.get('LOCALAPPDATA') or ''
        program_files = os.environ.get('ProgramFiles') or r'C:\Program Files'
        candidates = [
            os.path.join(local, 'Programs', 'Ollama', 'ollama.exe'),
            os.path.join(program_files, 'Ollama', 'ollama.exe'),
        ]
    else:
        candidates = ['/usr/local/bin/ollama', '/usr/bin/ollama', '/opt/homebrew/bin/ollama']
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _total_memory_gb():
    """Объём ОЗУ в ГБ (Windows - GlobalMemoryStatusEx, Linux - /proc/meminfo)."""
    try:
        if os.name == 'nt':
            import ctypes

            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]

            status = _MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return round(status.ullTotalPhys / (1024 ** 3), 1)
        else:
            with open('/proc/meminfo', 'r', encoding='utf-8') as fh:
                for line in fh:
                    if line.startswith('MemTotal:'):
                        return round(int(line.split()[1]) / (1024 ** 2), 1)
    except Exception:
        pass
    return 0.0


def _dir_size_bytes(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total


def _disk_free_gb(path):
    try:
        probe = path
        while probe and not os.path.exists(probe):
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        return round(shutil.disk_usage(probe or '.').free / (1024 ** 3), 1)
    except Exception:
        return 0.0


def recommend_whisper_size(memory_gb, device='cpu'):
    """Подбирает размер модели под железо (без ручных настроек)."""
    budget = memory_gb or 0
    if device == 'cuda':
        # На GPU модель занимает меньше RAM, можно брать крупнее.
        budget = budget * 1.6
    if budget >= 14:
        return 'large-v3'
    if budget >= 9:
        return 'medium'
    if budget >= 6:
        return 'small'
    return 'base'


def create_blueprint(*, model_dir, default_model_size, llm_model, ollama_url,
                     logger=None, ffmpeg_path=None, allowed_sizes=None,
                     device_provider=None, active_model_getter=None,
                     active_model_setter=None, ffmpeg_installer=None,
                     binary_refresh=None):
    """Создаёт Blueprint управления моделями.

    device_provider - функция без аргументов, возвращающая (device, compute_type);
    нужна, чтобы не импортировать app.py и не дублировать определение видеокарты.
    ffmpeg_path - путь к ffmpeg или функция без аргументов (путь меняется
    после скачивания бинарника из GUI); ffmpeg_installer - модуль binaries.py
    с install()/status(); binary_refresh - пересчёт путей в config после установки.
    """
    log = logger or logging.getLogger(__name__)
    allowed = set(allowed_sizes or WHISPER_CATALOG.keys())
    device_provider = device_provider or (lambda: ('cpu', 'int8'))
    os.makedirs(model_dir, exist_ok=True)

    tasks = {}
    tasks_lock = threading.Lock()
    automation_lock = threading.Lock()

    bp = Blueprint('models_api', __name__)

    def _active_model():
        """Модель для сводок: выбор пользователя из GUI или значение из config."""
        try:
            value = active_model_getter() if active_model_getter else None
        except Exception:  # noqa: BLE001 - настройки не должны ронять API
            value = None
        return str(value or llm_model)

    def _ffmpeg_binary():
        """Текущий путь к ffmpeg (значение или провайдер, если передан функцией)."""
        try:
            value = ffmpeg_path() if callable(ffmpeg_path) else ffmpeg_path
        except Exception:  # noqa: BLE001 - статус не должен ронять API
            value = None
        return str(value or '')

    def _ffmpeg_status():
        """Статус ffmpeg + возможность скачать его из GUI (как модели)."""
        path = _ffmpeg_binary()
        ok = bool(path) and (os.path.exists(path) or bool(shutil.which(path)))
        install_info = {'supported': False, 'hint': 'Скачивание бинарников недоступно'}
        version = None
        if ffmpeg_installer is not None:
            try:
                install_info = ffmpeg_installer.build_info()
                version = ffmpeg_installer.ffmpeg_version(path) if ok else None
            except Exception:  # noqa: BLE001 - сеть/платформа не должны ломать /api/setup
                pass
        return {'ok': ok, 'path': path, 'version': version, 'download': install_info,
                'task': _task_snapshot('ffmpeg'),
                'hint': None if ok else (install_info.get('hint') or
                                         'Нажмите «Скачать FFmpeg» - приложение сделает всё само')}

    def _refresh_binaries():
        if binary_refresh is None:
            return None
        try:
            return binary_refresh()
        except Exception as exc:  # noqa: BLE001
            log.warning(f'Не удалось обновить пути к бинарникам: {exc}')
            return None

    def _run_ffmpeg_download(key):
        """Скачивание ffmpeg в фоне: прогресс виден в /api/models/tasks."""
        _set_task(key, status='running', label='FFmpeg', status_text='Подготовка',
                  progress=0, downloaded_mb=0, total_mb=0)
        try:
            result = ffmpeg_installer.install(progress=lambda **fields: _set_task(key, **fields))
            _refresh_binaries()
            _set_task(key, status='done', progress=100, status_text='Готово',
                      path=result.get('ffmpeg', ''), version=result.get('version'))
            log.info(f"FFmpeg установлен: {result.get('version')} ({result.get('ffmpeg')})")
        except Exception as exc:  # noqa: BLE001 - ошибку показываем в UI
            log.error(f'Установка FFmpeg не удалась: {exc}')
            _set_task(key, status='error', progress=0, error=str(exc))

    def _set_active_model(name):
        if active_model_setter:
            active_model_setter(name)

    # --- вспомогательные функции ---

    def _model_path(size):
        return os.path.join(model_dir, size)

    def _is_model_present(size):
        path = _model_path(size)
        if not os.path.isdir(path):
            return False
        return all(os.path.exists(os.path.join(path, name)) for name in WHISPER_MODEL_FILES)

    def _local_sizes():
        return [size for size in WHISPER_CATALOG if size in allowed and _is_model_present(size)]

    def _ollama_status(timeout=2.0):
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=timeout)
            if response.status_code != 200:
                return False, []
            models = [m.get('name', '') for m in response.json().get('models', []) if m.get('name')]
            return True, models
        except Exception:
            return False, []

    def _has_model(models, name):
        short = name.split(':')[0]
        return any(m == name or m.split(':')[0] == short for m in models)

    def _set_task(key, **fields):
        with tasks_lock:
            task = tasks.setdefault(key, {'created_at': time.time()})
            task.update(fields)
            task['updated_at'] = time.time()
            return dict(task)

    def _task_snapshot(key):
        with tasks_lock:
            task = tasks.get(key)
            return dict(task) if task else None

    def _percent(done_bytes, total_bytes):
        if not total_bytes:
            return 0
        return max(0, min(99, int(done_bytes * 100 / total_bytes)))

    def _wait_for_ollama(timeout=25.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            ok, models = _ollama_status(timeout=1.5)
            if ok:
                return True, models
            time.sleep(1.0)
        return False, []

    def start_ollama():
        """Поднимает `ollama serve`, если бинарник есть, но сервис не отвечает."""
        ok, models = _ollama_status()
        if ok:
            return {'ok': True, 'already_running': True, 'models': models}
        binary = _find_ollama_binary()
        if not binary:
            return {'ok': False, 'error': 'Ollama не установлена',
                    'hint': 'Установите: winget install Ollama.Ollama (или скачайте с ollama.com)',
                    'binary': None}
        with automation_lock:
            ok, models = _ollama_status()  # повторная проверка под локом
            if ok:
                return {'ok': True, 'already_running': True, 'models': models, 'binary': binary}
            try:
                creationflags = 0
                if os.name == 'nt':
                    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | \
                        getattr(subprocess, 'DETACHED_PROCESS', 0)
                subprocess.Popen(
                    [binary, 'serve'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                    creationflags=creationflags, close_fds=(os.name != 'nt'),
                )
                log.info(f"Запущена Ollama: {binary} serve")
            except Exception as exc:
                log.error(f"Не удалось запустить Ollama: {exc}")
                return {'ok': False, 'error': f'Не удалось запустить Ollama: {exc}', 'binary': binary}
        ok, models = _wait_for_ollama()
        if not ok:
            return {'ok': False, 'binary': binary,
                    'error': 'Ollama запущена, но не отвечает',
                    'hint': f'Проверьте адрес {ollama_url} (переменная OLLAMA_URL)'}
        return {'ok': True, 'already_running': False, 'models': models, 'binary': binary}

    def _download_whisper(size, target_dir, key, total_bytes):
        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:  # pragma: no cover - зависит от окружения
            raise RuntimeError('Нужен пакет huggingface_hub (ставится вместе с faster-whisper)') from exc
        repo = WHISPER_CATALOG[size]['repo']
        os.makedirs(target_dir, exist_ok=True)
        kwargs = {'repo_id': repo, 'local_dir': target_dir}
        try:
            snapshot_download(**kwargs, local_dir_use_symlinks=False)
        except TypeError:
            # huggingface_hub >= 0.23 убрал аргумент local_dir_use_symlinks
            snapshot_download(**kwargs)

    def _run_whisper_download(size, key):
        total_bytes = int(WHISPER_CATALOG[size]['size_mb'] * 1024 * 1024)
        target_dir = _model_path(size)
        done = threading.Event()
        _set_task(key, status='running', progress=0, downloaded_mb=0, total_mb=WHISPER_CATALOG[size]['size_mb'],
                  label=f'Whisper {size}')
        error_holder = {}

        def worker():
            try:
                _download_whisper(size, target_dir, key, total_bytes)
            except Exception as exc:  # noqa: BLE001 - ошибку показываем в UI
                error_holder['error'] = str(exc)
                log.error(f"Скачивание Whisper '{size}' не удалось: {exc}")
            finally:
                done.set()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        while not done.wait(1.5):
            downloaded = _dir_size_bytes(target_dir)
            _set_task(key, downloaded_mb=round(downloaded / (1024 * 1024), 1),
                      progress=_percent(downloaded, total_bytes))
        if error_holder:
            _set_task(key, status='error', error=error_holder['error'], progress=0)
            return
        if _is_model_present(size):
            _set_task(key, status='done', progress=100, downloaded_mb=WHISPER_CATALOG[size]['size_mb'])
            log.info(f"Модель Whisper '{size}' скачана в {target_dir}")
        else:
            _set_task(key, status='error', error='Файлы модели не найдены после скачивания')

    def _run_ollama_pull(model, key, activate=False):
        _set_task(key, status='running', progress=0, label=f'Ollama {model}', status_text='Подготовка')
        try:
            with requests.post(f"{ollama_url}/api/pull", json={'model': model, 'stream': True},
                               stream=True, timeout=(10, 3600)) as response:
                if response.status_code != 200:
                    _set_task(key, status='error', error=f'Ollama вернула HTTP {response.status_code}')
                    return
                for raw in response.iter_lines():
                    if not raw:
                        continue
                    try:
                        chunk = json.loads(raw.decode('utf-8', 'ignore'))
                    except ValueError:
                        continue
                    if chunk.get('error'):
                        _set_task(key, status='error', error=str(chunk['error']))
                        return
                    total = chunk.get('total') or 0
                    completed = chunk.get('completed') or 0
                    _set_task(key, status_text=chunk.get('status') or '',
                              progress=_percent(completed, total),
                              downloaded_mb=round(completed / (1024 * 1024), 1),
                              total_mb=round(total / (1024 * 1024), 1))
            if activate:
                try:
                    _set_active_model(model)
                except ValueError:
                    pass
            _set_task(key, status='done', progress=100)
            log.info(f"Модель Ollama '{model}' скачана")
        except Exception as exc:  # noqa: BLE001
            log.error(f"Скачивание модели Ollama '{model}' не удалось: {exc}")
            _set_task(key, status='error',
                      error=f'Не удалось скачать модель: {exc}. Проверьте, что Ollama запущена.')

    def _run_ollama_import(name, url, key, activate=True):
        """Скачивание GGUF по ссылке + `ollama create` (модель появляется в списке Ollama)."""
        target_dir = os.path.join(model_dir, 'gguf')
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, f'{name}.gguf')
        modelfile = None
        _set_task(key, status='running', progress=0, label=f'Импорт {name}', status_text='Скачивание')
        try:
            with requests.get(url, stream=True, allow_redirects=True, timeout=(20, 120),
                              headers={'User-Agent': 'Cutline'}) as response:
                if response.status_code != 200:
                    raise RuntimeError(f'Сервер вернул HTTP {response.status_code}')
                total = int(response.headers.get('Content-Length') or 0)
                free_gb = _disk_free_gb(model_dir)
                if total and free_gb and free_gb * (1024 ** 3) < total * 1.1:
                    raise RuntimeError(
                        f'Недостаточно места: нужно ~{total / (1024 ** 3):.1f} ГБ, '
                        f'свободно {free_gb:.1f} ГБ')
                downloaded = 0
                with open(target, 'wb') as fh:
                    for chunk in response.iter_content(1024 * 1024):
                        if not chunk:
                            continue
                        fh.write(chunk)
                        downloaded += len(chunk)
                        _set_task(key, downloaded_mb=round(downloaded / (1024 * 1024), 1),
                                  total_mb=round(total / (1024 * 1024), 1),
                                  progress=_percent(downloaded, total))
            binary = _find_ollama_binary()
            if not binary:
                raise RuntimeError('Ollama не установлена: для импорта нужен `ollama create`')
            started = start_ollama()
            if not started.get('ok'):
                raise RuntimeError(started.get('error') or 'Ollama не отвечает')
            _set_task(key, status_text='Создание модели', progress=95)
            modelfile = os.path.join(target_dir, f'{name}.Modelfile')
            with open(modelfile, 'w', encoding='utf-8') as fh:
                fh.write(f'FROM "{target}"\n')
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
            result = subprocess.run([binary, 'create', name, '-f', modelfile],
                                    capture_output=True, text=True, timeout=3600,
                                    creationflags=creationflags)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or '').strip().splitlines()
                raise RuntimeError('ollama create: ' + (detail[-1] if detail else f'код {result.returncode}'))
            if activate:
                try:
                    _set_active_model(name)
                except ValueError:
                    pass
            _set_task(key, status='done', progress=100)
            log.info(f"Модель '{name}' импортирована из {url}")
        except Exception as exc:  # noqa: BLE001 - ошибку показываем в UI
            log.error(f"Импорт модели '{name}' не удался: {exc}")
            _set_task(key, status='error', error=str(exc), progress=0)
        finally:
            for path in (target, modelfile):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    # --- роуты ---

    @bp.route('/api/setup')
    def setup_status():
        device, compute_type = device_provider()
        memory_gb = _total_memory_gb()
        recommended = recommend_whisper_size(memory_gb, device)
        ffmpeg_state = _ffmpeg_status()
        ffmpeg_ok = ffmpeg_state['ok']
        ollama_ok, ollama_models = _ollama_status()
        local_sizes = _local_sizes()
        default_ready = _is_model_present(default_model_size)
        binary = _find_ollama_binary()

        warnings = []
        if not ffmpeg_ok:
            warnings.append('ffmpeg не найден: обработка медиа невозможна')
        if not default_ready and not local_sizes:
            warnings.append(f'Модель Whisper "{default_model_size}" не скачана')
        if not ollama_ok:
            warnings.append('Ollama недоступна: сводки и расшифровка текста без неё не работают')
        elif not _has_model(ollama_models, _active_model()):
            warnings.append(f'Модель Ollama "{_active_model()}" не скачана')

        return jsonify({
            'platform': {
                'os': platform.system(),
                'release': platform.release(),
                'python': sys.version.split()[0],
                'frozen': bool(getattr(sys, 'frozen', False)),
                'app_dir': os.path.dirname(os.path.abspath(__file__)),
            },
            'memory_gb': memory_gb,
            'disk_free_gb': _disk_free_gb(model_dir),
            'device': device,
            'compute_type': compute_type,
            'recommended_size': recommended,
            'ffmpeg': ffmpeg_state,
            'whisper': {
                'model_dir': model_dir,
                'default_size': default_model_size,
                'default_ready': default_ready,
                'local_sizes': local_sizes,
                'catalog': [
                    {'size': size, **{k: v for k, v in meta.items() if k != 'repo'},
                     'present': _is_model_present(size), 'recommended': size == recommended}
                    for size, meta in WHISPER_CATALOG.items() if size in allowed
                ],
            },
            'ollama': {
                'url': ollama_url,
                'running': ollama_ok,
                'binary': binary,
                'models': ollama_models,
                'model': _active_model(),
                'model_ready': _has_model(ollama_models, _active_model()),
                'catalog': OLLAMA_CATALOG,
                'hint': None if binary else 'Установите Ollama: winget install Ollama.Ollama',
            },
            'ready': ffmpeg_ok and (default_ready or bool(local_sizes)) and ollama_ok,
            'warnings': warnings,
        })

    @bp.route('/api/models')
    def models_catalog():
        ollama_ok, ollama_models = _ollama_status()
        return jsonify({
            'whisper': {
                'default_size': default_model_size,
                'local_sizes': _local_sizes(),
                'catalog': [{'size': size, **{k: v for k, v in meta.items() if k != 'repo'},
                             'present': _is_model_present(size)}
                            for size, meta in WHISPER_CATALOG.items() if size in allowed],
            },
            'ollama': {
                'url': ollama_url,
                'running': ollama_ok,
                'models': ollama_models,
                'model': _active_model(),
                'model_ready': _has_model(ollama_models, _active_model()),
                'catalog': OLLAMA_CATALOG,
            },
        })

    @bp.route('/api/models/whisper/download', methods=['POST'])
    def download_whisper():
        payload = request.get_json(silent=True) or request.form or {}
        size = str(payload.get('size') or '').strip()
        if size not in WHISPER_CATALOG or size not in allowed:
            return jsonify({'error': 'Неизвестный размер модели', 'allowed': sorted(allowed)}), 400
        key = f'whisper:{size}'
        if _is_model_present(size):
            return jsonify({'success': True, 'already': True, 'size': size})
        current = _task_snapshot(key)
        if current and current.get('status') == 'running':
            return jsonify({'success': True, 'already': True, 'running': True, 'size': size})
        threading.Thread(target=_run_whisper_download, args=(size, key), daemon=True).start()
        return jsonify({'success': True, 'size': size, 'repo': WHISPER_CATALOG[size]['repo']})

    @bp.route('/api/models/ollama/pull', methods=['POST'])
    def pull_ollama_model():
        payload = request.get_json(silent=True) or request.form or {}
        model = str(payload.get('model') or '').strip()
        if not model or not _MODEL_NAME_RE.fullmatch(model):
            return jsonify({'error': 'Некорректное имя модели'}), 400
        ok, models = _ollama_status()
        if not ok:
            started = start_ollama()
            if not started.get('ok'):
                return jsonify({'error': started.get('error'), 'hint': started.get('hint')}), 503
            models = started.get('models', [])
        if _has_model(models, model):
            return jsonify({'success': True, 'already': True, 'model': model})
        key = f'ollama:{model}'
        current = _task_snapshot(key)
        if current and current.get('status') == 'running':
            return jsonify({'success': True, 'already': True, 'running': True, 'model': model})
        activate = bool(payload.get('activate'))
        threading.Thread(target=_run_ollama_pull, args=(model, key, activate), daemon=True).start()
        return jsonify({'success': True, 'model': model})

    @bp.route('/api/models/ollama/active', methods=['POST'])
    def set_active_model():
        """Выбирает уже скачанную модель для сводок (без правки конфигов)."""
        payload = request.get_json(silent=True) or request.form or {}
        model = str(payload.get('model') or '').strip()
        if not model or not _MODEL_NAME_RE.fullmatch(model):
            return jsonify({'error': 'Некорректное имя модели'}), 400
        ok, models = _ollama_status()
        if not ok:
            started = start_ollama()
            if not started.get('ok'):
                return jsonify({'error': started.get('error') or 'Ollama недоступна',
                                'hint': started.get('hint')}), 503
            models = started.get('models', [])
        if not _has_model(models, model):
            return jsonify({'error': f'Модели «{model}» нет в Ollama - сначала скачайте её',
                            'models': models}), 404
        try:
            _set_active_model(model)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        log.info(f"Активная LLM-модель: {model}")
        return jsonify({'success': True, 'model': model})

    @bp.route('/api/models/ollama/import', methods=['POST'])
    def import_ollama_model():
        """Импорт GGUF по прямой ссылке: скачиваем файл и создаём модель ollama."""
        payload = request.get_json(silent=True) or request.form or {}
        url = str(payload.get('url') or '').strip()
        name = str(payload.get('name') or '').strip()
        if not re.match(r'^https?://', url, re.I):
            return jsonify({'error': 'Нужна прямая ссылка http(s) на файл .gguf'}), 400
        if not name:
            name = os.path.basename(url.split('?')[0].split('#')[0])
            name = re.sub(r'\.gguf$', '', name, flags=re.I)
        name = re.sub(r'[^A-Za-z0-9._-]+', '-', name).strip('-.').lower()[:64]
        if not name or not _MODEL_NAME_RE.fullmatch(name):
            return jsonify({'error': 'Укажите имя модели: латиница, цифры, точка, дефис'}), 400
        if not _find_ollama_binary():
            return jsonify({'error': 'Ollama не установлена',
                            'hint': 'Импорт GGUF по ссылке выполняет `ollama create`. '
                                    'Установите Ollama: winget install Ollama.Ollama'}), 503
        key = f'ollama-import:{name}'
        current = _task_snapshot(key)
        if current and current.get('status') == 'running':
            return jsonify({'success': True, 'already': True, 'running': True, 'model': name})
        threading.Thread(target=_run_ollama_import, args=(name, url, key), daemon=True).start()
        return jsonify({'success': True, 'model': name, 'url': url})

    @bp.route('/api/models/tasks')
    def models_tasks():
        with tasks_lock:
            return jsonify({key: dict(value) for key, value in tasks.items()})

    # --- Бинарные зависимости (ffmpeg не входит в дистрибутив, как и модели) ---

    @bp.route('/api/binaries/ffmpeg')
    def ffmpeg_status():
        return jsonify(_ffmpeg_status())

    @bp.route('/api/binaries/ffmpeg/download', methods=['POST'])
    def ffmpeg_download():
        """Скачивает ffmpeg/ffprobe в каталог данных (аналог скачивания моделей)."""
        if ffmpeg_installer is None:
            return jsonify({'error': 'Скачивание FFmpeg недоступно',
                            'hint': 'Соберите приложение с модулем binaries.py'}), 503
        if _ffmpeg_status()['ok']:
            return jsonify({'success': True, 'already': True})
        info = ffmpeg_installer.build_info()
        if not info.get('supported'):
            return jsonify({'error': 'Нет готовой сборки FFmpeg для этой системы',
                            'hint': info.get('hint')}), 400
        key = 'ffmpeg'
        current = _task_snapshot(key)
        if current and current.get('status') == 'running':
            return jsonify({'success': True, 'already': True, 'running': True})
        threading.Thread(target=_run_ffmpeg_download, args=(key,), daemon=True).start()
        return jsonify({'success': True, 'url': info.get('url'), 'size_mb': info.get('size_mb')})

    @bp.route('/api/ollama/start', methods=['POST'])
    def ollama_start():
        result = start_ollama()
        return jsonify(result), (200 if result.get('ok') else 503)

    return bp
