@echo off
rem ============================================================
rem  Cutline: сборка desktop-оболочки (Tauri 2, WebView2)
rem
rem    packaging\build_tauri.bat              - установщик NSIS (dist\Cutline-Desktop-Setup-*.exe)
rem    packaging\build_tauri.bat portable     - portable exe + ZIP dist\Cutline-portable-*-win64.zip
rem
rem  Portable-вариант кладёт "Cutline Desktop.exe" внутрь dist\Cutline,
rem  поэтому оболочка запускает сервер из своей же папки.
rem
rem  ВАЖНО: внутри блоков if (...) нельзя писать круглые скобки в тексте
rem  echo - cmd.exe обрывает блок. Поэтому здесь только goto-переходы.
rem ============================================================
setlocal
cd /d "%~dp0.."

set MODE=installer
if /i "%~1"=="portable" set MODE=portable
if /i "%~1"=="--portable" set MODE=portable

echo [1/4] Проверяю сборку сервера ...
if exist "dist\Cutline\Cutline.exe" goto :server_ok
echo       dist\Cutline\Cutline.exe не найден - собираю сервер ...
call packaging\build_windows.bat
if errorlevel 1 goto :error
goto :cli
:server_ok
echo       OK: dist\Cutline\Cutline.exe

:cli
echo [2/4] Ищу Tauri CLI ...
set TAURI=npx --yes @tauri-apps/cli@2
cargo tauri --version >nul 2>nul
if not errorlevel 1 set TAURI=cargo tauri
echo       %TAURI%

echo [3/4] Собираю оболочку: %MODE%
if /i "%MODE%"=="portable" goto :portable
goto :installer

:portable
pushd tauri\src-tauri
rem npx - это .cmd-шим: без call управление не вернётся в этот скрипт
call %TAURI% build --no-bundle
if errorlevel 1 goto :error_popd
copy /y "target\release\cutline-desktop.exe" "..\..\dist\Cutline\Cutline Desktop.exe" >nul
if errorlevel 1 goto :error_popd
popd
echo [4/4] Собираю portable ZIP ...
python packaging\make_portable.py
if errorlevel 1 goto :error
echo.
echo Готово:
echo   dist\Cutline\Cutline Desktop.exe
echo   dist\Cutline-portable-1.0.0-win64.zip
exit /b 0

:error_popd
popd
goto :error

:installer
pushd tauri\src-tauri
rem npx - это .cmd-шим: без call управление не вернётся в этот скрипт
call %TAURI% build
if errorlevel 1 goto :error_popd
popd
copy /y "tauri\src-tauri\target\release\bundle\nsis\Cutline_1.0.0_x64-setup.exe" "dist\Cutline-Desktop-Setup-1.0.0.exe" >nul
if errorlevel 1 goto :error
echo [4/4] Готово: dist\Cutline-Desktop-Setup-1.0.0.exe
echo       Внимание: это установщик ТОЛЬКО оболочки, около 1 МБ. Полный дистрибутив
echo       для пользователя - Inno Setup packaging\cutline.iss или portable ZIP.
exit /b 0

:error
echo.
echo СБОРКА ОБОЛОЧКИ НЕ УДАЛАСЬ. Смотрите сообщения выше.
exit /b 1
