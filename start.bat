@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Cutline

rem --- 1. Проверяем, что виртуальное окружение рабочее ---
set "PY=.venv\Scripts\python.exe"
"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo [1/3] Готовлю виртуальное окружение...
    if exist .venv rmdir /s /q .venv
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo.
        echo ОШИБКА: не найден Python 3.10+. Установите его с https://python.org
        goto :end
    )
)

rem --- 2. Зависимости (ставятся только при первом запуске) ---
"%PY%" -c "import flask, faster_whisper, pydub, requests" >nul 2>&1
if errorlevel 1 (
    echo [2/3] Устанавливаю зависимости, это может занять несколько минут...
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -r req.txt
    if errorlevel 1 (
        echo.
        echo ОШИБКА: не удалось установить зависимости.
        goto :end
    )
)

if not exist uploads mkdir uploads
if not exist processed mkdir processed
if not exist temp_chunks mkdir temp_chunks
if not exist cache_transcripts mkdir cache_transcripts

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo ВНИМАНИЕ: ffmpeg не найден в PATH.
    echo Установите: winget install Gyan.FFmpeg   или   choco install ffmpeg
    echo.
)

echo [3/3] Запускаю Cutline на http://127.0.0.1:5000
echo При первом запуске модель Whisper скачается автоматически.
echo.
"%PY%" run.py

:end
echo.
echo Окно можно закрыть.
pause
