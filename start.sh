#!/usr/bin/env bash
# Быстрый старт Cutline из исходников: Linux / macOS.
# Windows: start.bat
#
#   ./start.sh
#
# Скрипт сам создаст .venv, поставит зависимости и поднимет сервер
# на http://127.0.0.1:5000 (порт меняется переменной PORT).
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python
PYTHON_BIN=${PYTHON:-python3}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ОШИБКА: не найден $PYTHON_BIN. Установите Python 3.10+ и повторите." >&2
    exit 1
fi

# --- 1. Виртуальное окружение ---
if [ ! -x "$PY" ] || ! "$PY" -c "import sys" >/dev/null 2>&1; then
    echo "[1/3] Готовлю виртуальное окружение..."
    rm -rf .venv
    "$PYTHON_BIN" -m venv .venv
    PY=.venv/bin/python
fi

# --- 2. Зависимости (ставятся только при первом запуске) ---
if ! "$PY" -c "import flask, faster_whisper, pydub, requests" >/dev/null 2>&1; then
    echo "[2/3] Устанавливаю зависимости, это может занять несколько минут..."
    "$PY" -m pip install --upgrade pip
    "$PY" -m pip install -r req.txt
fi

mkdir -p uploads processed temp_chunks cache_transcripts

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo
    echo "ВНИМАНИЕ: ffmpeg не найден в PATH."
    echo "  macOS:  brew install ffmpeg"
    echo "  Debian: sudo apt install ffmpeg"
    echo "  Fedora: sudo dnf install ffmpeg"
    echo
fi

echo "[3/3] Запускаю Cutline на http://127.0.0.1:${PORT:-5000}"
echo "При первом запуске модель Whisper скачается автоматически."
echo
exec "$PY" run.py
