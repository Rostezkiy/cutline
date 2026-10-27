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

### Windows — установщик (рекомендуется)

1. Скачайте `Cutline-Setup-*.exe` со страницы [Releases](../../releases) и запустите.
2. Запустите **Cutline**. При первом старте откроется мастер настройки.
3. Нажмите «Скачать» у FFmpeg, модели распознавания речи и LLM — всё скачается само.

Конфиги править не нужно: модели, бинарники и результаты хранятся в `%LOCALAPPDATA%\Cutline`.

### Windows — portable

Распакуйте `Cutline-portable-*-win64.zip` и запустите `Cutline Portable.cmd` (или `Cutline.exe` для работы
в браузере). Настройки и модели будут лежать рядом с программой, в папке `data`. Внутри архива есть
и настольная оболочка `Cutline Desktop.exe`.

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
packaging\build_tauri.bat        # оболочка Tauri      -> dist\Cutline-Desktop-Setup-*.exe
packaging\make_portable.py       # portable ZIP        -> dist\Cutline-portable-*.zip
iscc packaging\cutline.iss       # полный установщик   -> dist\Cutline-Setup.exe
```

Релиз собирается автоматически на тег `v*`: в GitHub Releases попадают переносимый архив
`Cutline-portable-<версия>-win64.zip` (сервер + настольная оболочка) и установщик
`Cutline-Setup-<версия>.exe`.

## Лицензия

[MIT](LICENSE)
