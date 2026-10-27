"""Настройки Cutline: пути, переменные окружения, константы и логирование."""

import logging
import os
import shutil
import sys

# pydub импортируется ниже, после настройки PATH/путей к ffmpeg (см. блок настроек).


# faster_whisper импортируется лениво (см. get_whisper_model): старт сервера
# не должен падать, если пакет/модель отсутствуют или качаются впервые.

# --- CONFIGURATION (всё переопределяется переменными окружения) ---
def _resource_dir():
    """Каталог ресурсов (templates/, бинарники): для PyInstaller - папка сборки."""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


def _migrate_legacy_data_dir(new_dir, old_dir):
    """Переименование проекта Cutline (ранее Unword): переносим данные пользователя.

    Модели и настройки весят гигабайты, поэтому при первом запуске новой версии
    старый каталог просто переименовывается. Если переименовать не вышло
    (файл занят, разные диски), данные копируются, а старый каталог остаётся.
    """
    if not os.path.isdir(old_dir) or os.path.exists(new_dir):
        return new_dir
    try:
        os.rename(old_dir, new_dir)
        logging.getLogger(__name__).info(f"Данные перенесены из {old_dir} в {new_dir}")
        return new_dir
    except OSError:
        pass
    try:
        shutil.copytree(old_dir, new_dir, dirs_exist_ok=True)
        logging.getLogger(__name__).warning(
            f"Данные скопированы из {old_dir} в {new_dir}: старый каталог можно удалить")
    except OSError as exc:
        logging.getLogger(__name__).warning(f"Не удалось перенести данные из {old_dir}: {exc}")
    return new_dir


def _data_dir():
    """Каталог изменяемых данных (uploads/processed/models/logs).

    Установленная программа живёт в Program Files, куда писать нельзя,
    поэтому в собранном виде данные уходят в каталог пользователя
    (%LOCALAPPDATA%/Cutline). Переопределяется переменной CUTLINE_DATA_DIR.
    """
    explicit = os.environ.get('CUTLINE_DATA_DIR')
    if explicit:
        return explicit
    if getattr(sys, 'frozen', False):
        base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
        return _migrate_legacy_data_dir(os.path.join(base, 'Cutline'),
                                        os.path.join(base, 'Unword'))
    return _resource_dir()


APP_DIR = _resource_dir()      # ресурсы: templates/, ffmpeg.exe рядом с программой
DATA_DIR = _data_dir()         # изменяемые данные: загрузки, результаты, модели
TEMPLATES_DIR = os.path.join(APP_DIR, 'templates')


# Каталог скачанных бинарников (ffmpeg/ffprobe). Лежит в данных пользователя:
# установленная программа может находиться в Program Files, куда писать нельзя.
BIN_DIR = os.environ.get('BIN_DIR') or os.path.join(DATA_DIR, 'bin')
if not os.path.isabs(BIN_DIR):
    BIN_DIR = os.path.join(DATA_DIR, BIN_DIR)


def _exe_name(binary_name):
    return f'{binary_name}.exe' if os.name == 'nt' else binary_name


def _known_locations(binary_name):
    """Известные места установки вне PATH (chocolatey, Homebrew, /usr/local)."""
    if os.name == 'nt':
        return [os.path.join(r'C:\ProgramData\chocolatey\bin', _exe_name(binary_name))]
    return [f'/usr/local/bin/{binary_name}', f'/opt/homebrew/bin/{binary_name}',
            f'/usr/bin/{binary_name}']


def _resolve_binary(env_name, binary_name):
    """Порядок поиска: env -> рядом с программой -> BIN_DIR -> PATH -> известные пути.

    BIN_DIR проверяется до PATH: бинарник, скачанный из GUI, должен побеждать
    системный, иначе версия на машине пользователя непредсказуема.
    """
    value = os.environ.get(env_name)
    if value:
        return value
    exe = _exe_name(binary_name)
    for candidate in (os.path.join(APP_DIR, exe), os.path.join(BIN_DIR, exe)):
        if os.path.exists(candidate):
            return candidate
    found = shutil.which(binary_name)
    if found:
        return found
    for candidate in _known_locations(binary_name):
        if os.path.exists(candidate):
            return candidate
    return binary_name


FFMPEG_PATH = _resolve_binary('FFMPEG_PATH', 'ffmpeg')
FFPROBE_PATH = _resolve_binary('FFPROBE_PATH', 'ffprobe')


def ffmpeg_path():
    """Актуальный путь к ffmpeg (меняется после скачивания бинарника из GUI)."""
    return FFMPEG_PATH


def ffprobe_path():
    """Актуальный путь к ffprobe."""
    return FFPROBE_PATH


def binary_exists(path):
    """Есть ли бинарник на диске или в PATH."""
    value = str(path or '')
    return bool(value) and (os.path.exists(value) or bool(shutil.which(value)))


def _register_binary_dirs():
    """Каталог с ffmpeg/ffprobe добавляем в PATH: его ищут pydub и дочерние процессы."""
    current = os.environ.get('PATH', '').split(os.pathsep)
    for path in (FFMPEG_PATH, FFPROBE_PATH):
        folder = os.path.dirname(path or '')
        if folder and os.path.isdir(folder) and folder not in current:
            os.environ['PATH'] = os.environ.get('PATH', '') + os.pathsep + folder
            current.append(folder)


def refresh_binary_paths():
    """Пересчитывает пути к ffmpeg/ffprobe и обновляет настройки pydub.

    Вызывается после установки/скачивания бинарников (см. binaries.py).
    """
    global FFMPEG_PATH, FFPROBE_PATH
    FFMPEG_PATH = _resolve_binary('FFMPEG_PATH', 'ffmpeg')
    FFPROBE_PATH = _resolve_binary('FFPROBE_PATH', 'ffprobe')
    _register_binary_dirs()
    try:
        AudioSegment.converter = FFMPEG_PATH
        AudioSegment.ffprobe = FFPROBE_PATH
    except NameError:  # pydub ещё не импортирован (очень ранний вызов)
        pass
    return {'ffmpeg': FFMPEG_PATH, 'ffprobe': FFPROBE_PATH,
            'available': binary_exists(FFMPEG_PATH)}


def _dir_setting(env_name, default):
    """Пути по умолчанию считаются от каталога проекта, а не от текущего cwd."""
    value = os.environ.get(env_name)
    if not value:
        return os.path.join(DATA_DIR, default)
    return value if os.path.isabs(value) else os.path.join(DATA_DIR, value)


UPLOAD_FOLDER = _dir_setting('UPLOAD_FOLDER', 'uploads')
OUTPUT_FOLDER = _dir_setting('OUTPUT_FOLDER', 'processed')
TEMP_FOLDER = _dir_setting('TEMP_FOLDER', 'temp_chunks')
CACHE_FOLDER = _dir_setting('CACHE_FOLDER', 'cache_transcripts')
JOBS_STORE = os.path.join(OUTPUT_FOLDER, 'jobs_store.json')

# Модели Whisper: локальная папка models/<size> в приоритете, иначе модель
# автоматически скачивается с HuggingFace при первом использовании.
WHISPER_MODEL_SIZE = os.environ.get('WHISPER_MODEL_SIZE', 'medium')
MODEL_DIR = _dir_setting('MODEL_DIR', 'models')

LLM_MODEL = os.environ.get('LLM_MODEL', 'gemma3')  # Модель Ollama для сводок (README: gemma3)
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')

MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '4'))           # Потоков на нарезку одного файла
MAX_CONCURRENT_JOBS = max(1, int(os.environ.get('MAX_CONCURRENT_JOBS', '2')))  # Параллельных задач
MAX_UPLOAD_MB = int(os.environ.get('MAX_UPLOAD_MB', '2048'))
MAX_FILES_PER_JOB = int(os.environ.get('MAX_FILES_PER_JOB', '50'))
UPLOAD_TTL_HOURS = int(os.environ.get('UPLOAD_TTL_HOURS', '24'))
KEEP_RESULTS = int(os.environ.get('KEEP_RESULTS', '40'))        # Сколько файлов хранить в processed/
MAX_JOB_HISTORY = int(os.environ.get('MAX_JOB_HISTORY', '100'))  # Сколько задач держать в истории
CACHE_TTL_DAYS = int(os.environ.get('CACHE_TTL_DAYS', '30'))      # Срок жизни кэша транскриптов
MAX_JOB_DETAILS = int(os.environ.get('MAX_JOB_DETAILS', '20'))    # Для скольких последних задач хранить транскрипт

# По умолчанию слушаем только localhost: для доступа по сети задайте HOST=0.0.0.0 + ACCESS_TOKEN.
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '5000'))
DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.opus', '.wma', '.aiff',
                      '.mp4', '.mov', '.avi', '.mkv', '.webm'}
ALLOWED_FORMATS = {'mp3', 'wav', 'ogg', 'flac', 'mp4'}
ALLOWED_MODES = {'remove', 'save', 'replace', 'summarize'}
ALLOWED_MODEL_SIZES = {'tiny', 'base', 'small', 'medium', 'large', 'large-v3'}

_register_binary_dirs()

# Импорт после настройки ffmpeg: иначе pydub ругается RuntimeWarning'ом на старте.
from pydub import AudioSegment  # noqa: E402
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH


for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER, CACHE_FOLDER]:
    os.makedirs(folder, exist_ok=True)

LOG_DIR = os.environ.get('LOG_DIR') or os.path.join(DATA_DIR, 'logs')


def _configure_logging():
    """Логи одновременно в консоль и в logs/cutline.log (ротация 5 МБ x 3)."""
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        from logging.handlers import RotatingFileHandler

        os.makedirs(LOG_DIR, exist_ok=True)
        handlers.append(RotatingFileHandler(os.path.join(LOG_DIR, 'cutline.log'),
                                            maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'))
    except Exception as exc:  # noqa: BLE001 - недоступная папка логов не ломает запуск
        print(f"Не удалось открыть файл лога: {exc}")
    for handler in handlers:
        handler.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=handlers)


_configure_logging()
logger = logging.getLogger(__name__)

# --- ДОСТУП (токен для сетевого режима) ---
# Если задан ACCESS_TOKEN, все запросы требуют токен: ?token=... или X-Access-Token.
# Нужен при HOST=0.0.0.0, когда программа доступна не только локально.
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN', '').strip()


def set_access_token(token):
    """Меняет токен доступа на лету (используется тестами и внешними скриптами)."""
    global ACCESS_TOKEN
    ACCESS_TOKEN = (token or '').strip()
    return ACCESS_TOKEN
