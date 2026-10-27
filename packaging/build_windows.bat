@echo off
rem ============================================================
rem  Cutline: сборка переносимой версии (PyInstaller onedir)
rem  Результат: dist\Cutline\Cutline.exe
rem  ffmpeg НЕ входит в сборку: пользователь скачивает его из GUI (кнопка в мастере).
rem  Для офлайн-дистрибутива положите ffmpeg/ffprobe в packaging\bin до сборки.
rem ============================================================
setlocal
cd /d "%~dp0.."

set VENV=.venv-build
if not exist "%VENV%\Scripts\python.exe" (
    echo [1/5] Создаю виртуальное окружение %VENV% ...
    python -m venv "%VENV%" || goto :error
)
call "%VENV%\Scripts\activate.bat"

echo [2/5] Обновляю pip и ставлю зависимости ...
python -m pip install --upgrade pip >nul || goto :error
python -m pip install -r req.txt pyinstaller || goto :error

echo [3/5] Тесты ...
python -m unittest discover -s tests || goto :error

echo [4/5] Сборка PyInstaller ...
pyinstaller --noconfirm --clean packaging\cutline.spec || goto :error

echo [5/5] Готово: dist\Cutline\Cutline.exe
echo Следующий шаг (опционально): установщик Inno Setup
echo    iscc packaging\cutline.iss
exit /b 0

:error
echo.
echo СБОРКА НЕ УДАЛАСЬ. Смотрите сообщения выше.
exit /b 1
