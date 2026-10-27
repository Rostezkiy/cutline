"""Ollama: сводка транскрипта и главы."""

import os
import time

import requests

from config import OLLAMA_URL, logger
from runtime_settings import get_llm_model
from transcribe import format_timestamp


def _ollama_generate(prompt, model_name):
    """Один запрос к Ollama, возвращает текст ответа или None."""
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3}
    }
    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip() or None
        logger.error(f"Ошибка Ollama: {response.status_code}")
    except Exception as e:
        logger.error(f"Ошибка соединения с Ollama: {e}")
    return None


def ollama_status(timeout=3):
    """Возвращает (доступна ли Ollama, список имён локальных моделей)."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=timeout)
        if r.status_code != 200:
            return False, []
        models = [m.get('name', '') for m in r.json().get('models', []) if m.get('name')]
        return True, models
    except Exception:
        return False, []


def ensure_ollama_model(model_name):
    """Проверяет наличие модели в Ollama; при OLLAMA_AUTO_PULL=1 скачивает её."""
    ok, models = ollama_status()
    if not ok:
        raise RuntimeError(
            f"Ollama недоступна по адресу {OLLAMA_URL}. Запустите Ollama (ollama serve) "
            f"или укажите адрес в переменной OLLAMA_URL.")
    short = model_name.split(':')[0]
    if any(m == model_name or m.split(':')[0] == short for m in models):
        return
    if os.environ.get('OLLAMA_AUTO_PULL', '0') == '1':
        logger.info(f"Модель '{model_name}' отсутствует в Ollama - скачиваю...")
        try:
            requests.post(f"{OLLAMA_URL}/api/pull", json={"model": model_name, "stream": False}, timeout=1800)
        except Exception as e:
            raise RuntimeError(f"Не удалось скачать модель '{model_name}': {e}")
        return
    raise RuntimeError(
        f"Модель '{model_name}' не найдена в Ollama. Выполните: ollama pull {model_name} "
        f"(или задайте OLLAMA_AUTO_PULL=1 для автоскачивания).")


def _split_text_chunks(full_text, chunk_size):
    """Разбивает текст на чанки по границам предложений."""
    char_limit = chunk_size * 4
    chunks = []
    start = 0
    while start < len(full_text):
        end = start + char_limit
        if end >= len(full_text):
            chunks.append(full_text[start:])
            break
        sentence_end = max(
            full_text.rfind('.', start, end),
            full_text.rfind('!', start, end),
            full_text.rfind('?', start, end),
            full_text.rfind('\n', start, end)
        )
        if sentence_end == -1 or sentence_end < start + char_limit // 2:
            sentence_end = end
        chunks.append(full_text[start:sentence_end + 1].strip())
        start = sentence_end + 1
        # Пропускаем пробелы/переносы: иначе при склейке чанков появляются
        # двойные пробелы и «смазанные» границы предложений
        while start < len(full_text) and full_text[start].isspace():
            start += 1
    return chunks


def _short_ts(seconds):
    return format_timestamp(seconds).split(',')[0]


def _summarize_chapters(segments, model_name, chunk_size, chapter_minutes):
    """Сводка с таймкодами глав: «о чём 10–20 минута»."""
    step = chapter_minutes * 60
    chapters = []
    current = []
    chapter_start = 0.0
    for seg in segments:
        if seg.get('end', 0) - chapter_start > step and current:
            chapters.append((chapter_start, seg['start'], current))
            current = []
            chapter_start = seg['start']
        current.append(seg)
    if current:
        chapters.append((chapter_start, segments[-1].get('end', chapter_start + step), current))

    parts = []
    for cs, ce, segs in chapters:
        text = " ".join(s['text'].strip() for s in segs)
        if not text.strip():
            continue
        prompt = (f"Сделай краткий пересказ фрагмента записи [{_short_ts(cs)} - {_short_ts(ce)}], "
                  f"сохраняя важные детали:\n\n{text}")
        summary = _ollama_generate(prompt, model_name) or "(нет ответа)"
        parts.append(f"## [{_short_ts(cs)} - {_short_ts(ce)}]\n{summary}")
        time.sleep(0.3)
    return "\n\n".join(parts) if parts else "Не удалось получить сводку."


def summarize_transcript(segments, model_name=None, chunk_size=4000, chapter_minutes=10):
    """
    Генерирует сводку текста через Ollama.
    segments: список сегментов транскрипта {'text': ..., 'start': ..., 'end': ...}
    Возвращает строку сводки. Для длинных записей - сводку по главам с таймкодами.
    """
    model_name = model_name or get_llm_model()
    ensure_ollama_model(model_name)  # понятная ошибка вместо «(нет ответа)»

    # Извлечение полного текста
    full_text = " ".join([seg['text'].strip() for seg in segments])
    if not full_text.strip():
        return "Текст отсутствует."

    # Длинные записи: сводка по главам с таймкодами
    total_end = segments[-1].get('end', 0) if segments else 0
    if total_end > chapter_minutes * 60:
        logger.info(f"Запись длиной {total_end:.0f}с - сводка по главам по {chapter_minutes} мин")
        return _summarize_chapters(segments, model_name, chunk_size, chapter_minutes)

    chunks = _split_text_chunks(full_text, chunk_size)
    logger.info(f"Разбивка текста на {len(chunks)} чанков")

    summaries = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Обработка чанка {i+1}/{len(chunks)}")
        summary = _ollama_generate(f"Сделай краткий пересказ следующего текста, сохраняя важные детали:\n\n{chunk}", model_name)
        summaries.append(summary or "(нет ответа)")
        time.sleep(0.5)

    if not summaries:
        return "Не удалось получить сводку."

    if len(summaries) == 1:
        return summaries[0]

    combined = " ".join(summaries)
    if len(combined) > chunk_size * 4:
        fake_segments = [{'text': combined}]
        return summarize_transcript(fake_segments, model_name, chunk_size)
    else:
        final = _ollama_generate(f"Сделай итоговый краткий пересказ, объединив следующие части:\n\n{combined}", model_name)
        return final or combined[:500] + "..."
