"""Скачивание ffmpeg/ffprobe в каталог данных (как модели, а не в дистрибутив).

Смысл: статическая сборка ffmpeg весит сотни мегабайт, а нужна не всем сразу.
Дистрибутив остаётся маленьким и полностью рабочим после одного клика в GUI:
бинарники качаются с официального зеркала BtbN (GitHub Releases) в BIN_DIR
(каталог данных пользователя) и сразу подхватываются приложением.

Размер архива и его вид (zip / tar.xz) зависят от платформы. macOS в готовых
сборках BtbN отсутствует - там предлагаем `brew install ffmpeg`.
"""

import os
import platform
import shutil
import subprocess
import tarfile
import zipfile

import requests

import config

# Зеркало статических сборок: ffmpeg + ffprobe в одном архиве.
BASE_URL = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'

# platform.system() -> machine (lower) -> (имя архива, тип упаковки, ~размер МБ)
ARCHIVES = {
    'Windows': {
        'amd64': ('ffmpeg-master-latest-win64-gpl.zip', 'zip', 190),
        'x86_64': ('ffmpeg-master-latest-win64-gpl.zip', 'zip', 190),
        'arm64': ('ffmpeg-master-latest-winarm64-gpl.zip', 'zip', 180),
        'aarch64': ('ffmpeg-master-latest-winarm64-gpl.zip', 'zip', 180),
    },
    'Linux': {
        'x86_64': ('ffmpeg-master-latest-linux64-gpl.tar.xz', 'tar', 85),
        'amd64': ('ffmpeg-master-latest-linux64-gpl.tar.xz', 'tar', 85),
        'aarch64': ('ffmpeg-master-latest-linuxarm64-gpl.tar.xz', 'tar', 80),
        'arm64': ('ffmpeg-master-latest-linuxarm64-gpl.tar.xz', 'tar', 80),
    },
}

DOWNLOAD_TIMEOUT = (20, 120)  # connect, read: медленные каналы не должны рвать загрузку


def _exe_name(name):
    return f'{name}.exe' if os.name == 'nt' else name


def _binary_names():
    return (_exe_name('ffmpeg'), _exe_name('ffprobe'))


def build_info():
    """Что и откуда качать на этой машине (без обращения к сети)."""
    system = platform.system()
    machine = (platform.machine() or '').lower()
    override = (os.environ.get('FFMPEG_DOWNLOAD_URL') or '').strip()
    entry = ARCHIVES.get(system, {}).get(machine)
    url = override or (BASE_URL + entry[0] if entry else '')
    kind = 'zip' if url.lower().endswith('.zip') else ('tar' if url else '')
    size_mb = entry[2] if entry and not override else 0
    supported = bool(url)
    if override:
        supported = True
    hint = None
    if not supported:
        if system == 'Darwin':
            hint = 'macOS: установите ffmpeg командой `brew install ffmpeg`'
        else:
            hint = (f'Для {system}/{platform.machine()} нет готовой сборки: '
                    'установите ffmpeg вручную или задайте FFMPEG_DOWNLOAD_URL')
    return {
        'supported': supported,
        'os': system,
        'arch': platform.machine(),
        'url': url,
        'archive': kind,
        'size_mb': size_mb,
        'install_dir': config.BIN_DIR,
        'hint': hint,
    }


def ffmpeg_version(path=None):
    """Версия установленного ffmpeg (первая строка `-version`) или None."""
    binary = path or config.ffmpeg_path()
    if not config.binary_exists(binary):
        return None
    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    try:
        result = subprocess.run([binary, '-version'], capture_output=True, text=True,
                                timeout=20, creationflags=creationflags)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    lines = (result.stdout or '').strip().splitlines()
    return lines[0].strip() if lines else None


def _download(url, target, progress=None):
    """Скачивает архив потоком, сообщая прогресс в процентах и мегабайтах."""
    with requests.get(url, stream=True, allow_redirects=True, timeout=DOWNLOAD_TIMEOUT,
                      headers={'User-Agent': 'Cutline'}) as response:
        if response.status_code != 200:
            raise RuntimeError(f'Сервер вернул HTTP {response.status_code} для {url}')
        total = int(response.headers.get('Content-Length') or 0)
        free_gb = _free_gb(config.BIN_DIR)
        if total and free_gb and free_gb * (1024 ** 3) < total * 2:
            raise RuntimeError(f'Недостаточно места: нужно ~{total / (1024 ** 3) * 2:.1f} ГБ, '
                               f'свободно {free_gb:.1f} ГБ')
        done = 0
        with open(target, 'wb') as fh:
            for chunk in response.iter_content(1024 * 256):
                if not chunk:
                    continue
                fh.write(chunk)
                done += len(chunk)
                if progress:
                    progress(downloaded_mb=round(done / (1024 * 1024), 1),
                             total_mb=round(total / (1024 * 1024), 1),
                             progress=_percent(done, total))
    if os.path.getsize(target) == 0:
        raise RuntimeError('Загруженный архив пуст: проверьте соединение')


def _free_gb(path):
    probe = path
    while probe and not os.path.exists(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    try:
        return round(shutil.disk_usage(probe or '.').free / (1024 ** 3), 1)
    except OSError:
        return 0.0


def _percent(done, total):
    if not total:
        return 0
    return max(1, min(99, int(done * 100 / total)))


def _extract_archive(archive_path, kind):
    """Достаёт только ffmpeg/ffprobe из архива в BIN_DIR."""
    os.makedirs(config.BIN_DIR, exist_ok=True)
    wanted = set(_binary_names())
    extracted = {}

    def _save(name, source):
        target = os.path.join(config.BIN_DIR, name)
        partial = target + '.part'
        with open(partial, 'wb') as dst:
            shutil.copyfileobj(source, dst)
        os.replace(partial, target)
        if os.name != 'nt':
            os.chmod(target, 0o755)
        extracted[name] = target

    if kind == 'zip':
        with zipfile.ZipFile(archive_path) as zf:
            for member in zf.infolist():
                name = os.path.basename(member.filename)
                if member.is_dir() or name not in wanted:
                    continue
                with zf.open(member) as source:
                    _save(name, source)
    else:
        with tarfile.open(archive_path, 'r:*') as tf:
            for member in tf.getmembers():
                name = os.path.basename(member.name)
                if not member.isfile() or name not in wanted:
                    continue
                source = tf.extractfile(member)
                if source is not None:
                    with source:
                        _save(name, source)

    missing = wanted - set(extracted)
    if missing:
        raise RuntimeError('В архиве нет файлов: ' + ', '.join(sorted(missing)))
    return extracted


def install(progress=None):
    """Скачивает и распаковывает ffmpeg/ffprobe в BIN_DIR.

    progress - необязательный колбэк, принимающий keyword-аргументы
    (progress, downloaded_mb, total_mb, status_text) для GUI.
    """

    def report(**fields):
        if progress:
            progress(**fields)

    info = build_info()
    if not info['supported']:
        raise RuntimeError(info['hint'] or 'Платформа не поддерживается')

    os.makedirs(config.BIN_DIR, exist_ok=True)
    download_dir = os.path.join(config.BIN_DIR, '.download')
    os.makedirs(download_dir, exist_ok=True)
    archive_path = os.path.join(download_dir, os.path.basename(info['url'].split('?')[0]) or 'ffmpeg-archive')

    try:
        report(status_text='Скачивание FFmpeg', progress=1)
        _download(info['url'], archive_path, progress=progress)
        report(status_text='Распаковка', progress=99)
        extracted = _extract_archive(archive_path, info['archive'])
        ffmpeg_file = _exe_name('ffmpeg')
        config.refresh_binary_paths()
        version = ffmpeg_version(extracted[ffmpeg_file])
        if not version:
            raise RuntimeError('Скачанный ffmpeg не запускается: архив повреждён или не подходит '
                               'для этой системы')
        report(status_text='Готово', progress=100)
        return {'ffmpeg': extracted[ffmpeg_file],
                'ffprobe': extracted.get(_exe_name('ffprobe'), ''),
                'version': version}
    finally:
        try:
            if os.path.exists(archive_path):
                os.remove(archive_path)
            if os.path.isdir(download_dir) and not os.listdir(download_dir):
                os.rmdir(download_dir)
        except OSError:
            pass


def status():
    """Состояние ffmpeg для GUI: установлен ли, версия, можно ли скачать."""
    info = build_info()
    path = config.ffmpeg_path()
    installed = config.binary_exists(path)
    return {
        'ok': installed,
        'path': str(path or ''),
        'version': ffmpeg_version(path) if installed else None,
        'download': info,
    }
