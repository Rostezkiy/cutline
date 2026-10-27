# Cutline

**Cutline** — локальный AI-редактор аудио и видео по тексту. Находит заданные слова в речи, вырезает,
запикивает или изолирует их, а также делает пересказ записи. Всё считается на вашем компьютере:
файлы никуда не загружаются.

---

## Возможности

- **Фильтр слов** — удалить, запикать или изолировать фрагменты, где звучит заданное слово (с учётом словоформ).
- **AI-пересказ** — краткое содержание длинных записей через локальную LLM (Ollama).
- **Пакетная обработка** — очередь из нескольких файлов, пауза и продолжение.
- **Экспорт** — готовое медиа, SRT (в том числе с подсветкой), TXT, JSON-отчёт и пересказ.
- **Приватность** — никаких облаков и телеметрии; работает офлайн после первой настройки.

## Установка

### Windows — portable (рекомендуется)

Установщик не нужен: всё лежит в одном архиве.

1. Скачайте `Cutline-portable-*-win64.zip` со страницы [Releases](../../releases) и распакуйте в любую папку
   (например, `D:\Cutline`).
2. Запустите `Cutline Portable.cmd` — откроется нативное окно (Tauri). Для работы в браузере запустите
   `Cutline.exe` и откройте <http://127.0.0.1:5000>.
3. При первом старте откроется мастер настройки: нажмите «Скачать» у FFmpeg, модели распознавания речи и LLM.

Конфиги править не нужно: настройки, модели и результаты лежат рядом с программой, в папке `data`.
Права администратора не требуются.

### Установщик Windows (опционально)

Если нужны ярлыки в меню «Пуск» и деинсталлятор — соберите установщик сами:
`packaging\build_tauri.bat` (NSIS) или `iscc packaging\cutline.iss` (Inno Setup).
В релизах установщик больше не публикуется: он дублирует portable-архив.

### Docker (Linux / NAS)

```bash
docker compose up -d
```

Откройте <http://localhost:5000>. Для доступа по сети задайте `ACCESS_TOKEN` (см. `docker-compose.yml`).

## Требования

- Windows 10/11 (или Linux/macOS при запуске из исходников или в Docker).
- 8 ГБ ОЗУ и ~6 ГБ диска для моделей (рекомендуется 16 ГБ для моделей `large`).
- Ollama нужна только для режима «Пересказ» — её можно запустить из мастера настройки.

## Запуск из исходников

Самый быстрый способ — скрипт запуска: он сам создаёт `.venv`, ставит зависимости и поднимает сервер.
Нужен только Python 3.10+ и ffmpeg в `PATH`.

```bash
start.bat      # Windows
./start.sh     # Linux / macOS
```

Приложение откроется на <http://127.0.0.1:5000>. Вручную то же самое:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r req.txt
python run.py
```

Полезные переменные окружения: `PORT`, `CUTLINE_DATA_DIR`, `WHISPER_MODEL_SIZE`, `LLM_MODEL`,
`OLLAMA_URL`, `ACCESS_TOKEN`, `MAX_CONCURRENT_JOBS`.

## Тесты

```bash
python -m unittest discover -s tests -v
```

## Сборка дистрибутива

```bash
packaging\build_windows.bat      # PyInstaller onedir  -> dist\Cutline\Cutline.exe
packaging\build_tauri.bat        # оболочка Tauri      -> dist\Cutline-Desktop-Setup-*.exe / Cutline Desktop.exe
packaging\make_portable.py       # portable ZIP        -> dist\Cutline-portable-*.zip
iscc packaging\cutline.iss       # альтернативный установщик -> dist\Cutline-Setup.exe
```

Релиз собирается автоматически на тег `v*`: в GitHub Releases попадает один архив
`Cutline-portable-<версия>-win64.zip` — сервер, настольная оболочка и launcher. Старые ассеты
предыдущих прогонов на тот же тег удаляются автоматически.

## Лицензия

[MIT](LICENSE)
