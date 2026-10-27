"""Сборка Cutline в один exe-каталог.

Запуск: `python run.py` (в Windows удобнее дважды щёлкнуть start.bat).
Скрипт проверяет зависимости, поднимает сервер и открывает браузер.
Тот же модуль используется и в собранной версии (PyInstaller onedir).
"""

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
FROZEN = bool(getattr(sys, 'frozen', False))


def _check_dependencies():
    try:
        import flask  # noqa: F401
        import requests  # noqa: F401
        import pydub  # noqa: F401
    except ImportError as exc:
        print("Не хватает зависимостей: %s" % exc)
        print("Установите их командой: pip install -r req.txt")
        return False
    return True


def _warn_missing_ffmpeg():
    exe = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
    search = [os.path.join(os.path.dirname(sys.executable), exe), os.path.join(APP_DIR, exe)]
    search += [os.path.join(path, exe) for path in os.environ.get('PATH', '').split(os.pathsep) if path]
    if not any(os.path.exists(path) for path in search):
        print("ВНИМАНИЕ: ffmpeg не найден - обработка медиа не будет работать.")
        print("Windows: winget install Gyan.FFmpeg  |  macOS: brew install ffmpeg")
        print("Linux: sudo apt install ffmpeg\n")


def main():
    # Каталог ресурсов: рядом с программой (в сборке - каталог exe).
    os.chdir(os.path.dirname(os.path.abspath(sys.executable)) if FROZEN else APP_DIR)
    os.environ.setdefault('OPEN_BROWSER', '1')

    if FROZEN:
        # В сборке app.py лежит внутри архива: импортируем модуль, а не путь.
        import app as cutline_app
        cutline_app.main()
        return 0

    if not _check_dependencies():
        return 1
    _warn_missing_ffmpeg()

    import app as cutline_app
    cutline_app.main()
    return 0


if __name__ == '__main__':
    sys.exit(main())
