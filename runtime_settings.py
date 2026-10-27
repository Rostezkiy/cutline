"""Настройки, которые пользователь меняет из GUI (переживают перезапуск).

Значения по умолчанию берутся из config.py (переменные окружения), но менять
конфиги вручную не нужно: выбор сохраняется в ``DATA_DIR/settings.json``.

Сейчас хранится один параметр - ``llm_model`` (модель Ollama для сводок).
Файл читается лениво и кэшируется, запись атомарная (temp + os.replace).
"""

import json
import os
import threading

from config import DATA_DIR, LLM_MODEL, logger

SETTINGS_PATH = os.path.join(DATA_DIR, 'settings.json')

_lock = threading.Lock()
_cache = None


def _read_file():
    try:
        with open(SETTINGS_PATH, encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        logger.warning(f"Не удалось прочитать {SETTINGS_PATH}: {exc}")
        return {}


def _load():
    global _cache
    if _cache is None:
        _cache = _read_file()
    return _cache


def _write(data):
    global _cache
    os.makedirs(os.path.dirname(SETTINGS_PATH) or '.', exist_ok=True)
    tmp = SETTINGS_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, SETTINGS_PATH)
    _cache = data


def get_settings():
    """Копия сохранённых настроек (без значений по умолчанию)."""
    with _lock:
        return dict(_load())


def get_llm_model():
    """Модель Ollama для сводок: выбор пользователя или LLM_MODEL из config."""
    with _lock:
        value = _load().get('llm_model')
    if isinstance(value, str) and value.strip():
        return value.strip()
    return LLM_MODEL


def set_llm_model(name):
    """Сохраняет выбранную модель. Возвращает нормализованное имя."""
    name = str(name or '').strip()
    if not name:
        raise ValueError('Пустое имя модели')
    with _lock:
        data = dict(_load())
        data['llm_model'] = name
        _write(data)
    logger.info(f"Настройка сохранена: llm_model={name}")
    return name


def reset():
    """Сбрасывает пользовательские настройки (нужно тестам и кнопке «сбросить»)."""
    with _lock:
        _write({})
