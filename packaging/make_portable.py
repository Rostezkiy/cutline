"""Собирает переносимую (portable) сборку Cutline из готового dist\\Cutline.

    python packaging/build_windows.py  ->  dist\\Cutline\\Cutline.exe
    python packaging/make_portable.py  [--model small] [--no-zip]

Что делает:
1. Добавляет в dist\\Cutline launcher «Cutline Portable.cmd», который держит все
   данные (загрузки, результаты, модели, логи) внутри папки программы: data\\.
2. По желанию копирует уже скачанную модель Whisper, чтобы не качать её заново.
3. Пакует всё в dist\\Cutline-portable-<версия>-win64.zip.

Переносимая версия запускается двойным щелчком и не требует установки.
"""

import argparse
import os
import shutil
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DIST = os.path.join(ROOT, 'dist', 'Cutline')
VERSION = '1.0.0'

LAUNCHER_NAME = 'Cutline Portable.cmd'
LAUNCHER = r'''@echo off
rem Переносимый запуск: все данные (включая модели) лежат в папке data рядом.
title Cutline
set "CUTLINE_DATA_DIR=%~dp0data"
if not exist "%CUTLINE_DATA_DIR%" mkdir "%CUTLINE_DATA_DIR%"
rem Если рядом лежит desktop-оболочка, запускаем её: она сама поднимет сервер
rem с теми же переменными окружения. Иначе - сервер с браузером.
if exist "%~dp0Cutline Desktop.exe" goto :desktop
goto :server

:desktop
start "" "%~dp0Cutline Desktop.exe"
goto :eof

:server
start "" "%~dp0Cutline.exe"
'''


def check_build():
    exe = os.path.join(DIST, 'Cutline.exe')
    if not os.path.exists(exe):
        sys.exit(f'Нет сборки: {exe}\nСначала запустите packaging\\build_windows.bat')
    return exe


def write_launcher():
    path = os.path.join(DIST, LAUNCHER_NAME)
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(LAUNCHER)
    return path


def copy_model(size):
    source = os.path.join(ROOT, 'models', size)
    if not os.path.isdir(source):
        print(f'Модель models\\{size} не найдена - пропускаю (скачается при первом запуске)')
        return None
    target = os.path.join(DIST, 'data', 'models', size)
    if os.path.isdir(target):
        print(f'Модель уже в сборке: {target}')
        return target
    print(f'Копирую модель {size} ({_dir_size(source)} МБ) ...')
    shutil.copytree(source, target)
    return target


def _dir_size(path):
    total = sum(os.path.getsize(os.path.join(root, f))
                for root, _, files in os.walk(path) for f in files)
    return round(total / 1048576)


def make_zip():
    archive = os.path.join(ROOT, 'dist', f'Cutline-portable-{VERSION}-win64')
    print('Пакуют архив (может занять минуту) ...')
    path = shutil.make_archive(archive, 'zip', root_dir=os.path.dirname(DIST),
                               base_dir=os.path.basename(DIST))
    return path


def main():
    parser = argparse.ArgumentParser(description='Переносимая сборка Cutline')
    parser.add_argument('--model', help='скопировать локальную модель Whisper (например: small)')
    parser.add_argument('--no-zip', action='store_true', help='не упаковывать в zip')
    args = parser.parse_args()

    check_build()
    print('Лаунчер:', write_launcher())
    if args.model:
        copy_model(args.model)
    if not args.no_zip:
        started = time.time()
        path = make_zip()
        print(f'Архив: {path} ({round(os.path.getsize(path) / 1048576)} МБ, '
              f'{round(time.time() - started)} с)')


if __name__ == '__main__':
    main()
