"""faster-whisper, субтитры и текстовая нормализация."""

import hashlib
import json
import os
import re
import threading
from collections import Counter

from config import CACHE_FOLDER, MODEL_DIR, WHISPER_MODEL_SIZE, logger
from jobstore import update_job
from media import get_duration


# --- MODEL & HELPERS ---
CUDA_LIBRARIES = (('cublas64_12.dll', 'cudnn_ops64_9.dll') if os.name == 'nt'
                  else ('libcublas.so.12', 'libcudnn_ops.so.9'))


def cuda_libraries_available():
    """Проверяет, что библиотеки CUDA/cuDNN реально загружаются.

    ctranslate2 подгружает их лениво: модель «создалась» без GPU-библиотек,
    а падает только на первом инференсе (cublas64_12.dll is not found).
    Предварительная проверка даёт работающий CPU-режим вместо ошибки задачи.
    Возвращает (True, None) или (False, имя_недостающей_библиотеки).
    """
    import ctypes

    for name in CUDA_LIBRARIES:
        try:
            (ctypes.WinDLL if os.name == 'nt' else ctypes.CDLL)(name)
        except OSError:
            return False, name
    return True, None


def _detect_device():
    """Определяет устройство для инференса без тяжёлой зависимости torch."""
    device = (os.environ.get('WHISPER_DEVICE') or '').strip()
    compute_type = (os.environ.get('WHISPER_COMPUTE_TYPE') or '').strip()
    if device:
        return device, compute_type or ("float16" if device == "cuda" else "int8")
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            libs_ok, missing = cuda_libraries_available()
            if libs_ok:
                return "cuda", compute_type or "float16"
            logger.warning(f"GPU найден, но библиотека {missing} недоступна - работаю на CPU. "
                           f"Для GPU нужны CUDA 12 + cuDNN 9 (или WHISPER_DEVICE=cpu).")
    except Exception as e:
        logger.debug(f"CUDA detection skipped: {e}")
    return "cpu", compute_type or "int8"


_device, _compute_type = _detect_device()
# Фактическое устройство: после отката на CPU отличается от выбранного выше.
_active_device, _active_compute_type = _device, _compute_type


def device_info():
    """Возвращает (device, compute_type), на которых реально работает Whisper."""
    return _active_device, _active_compute_type

_model_cache = {}
_model_lock = threading.Lock()
model_error = None


def _run_transcription(input_path, transcribe_kwargs, model_size, on_segment):
    """Транскрибация с одноразовым поворотом на CPU, если GPU падает в рантайме.

    ctranslate2 грузит CUDA-библиотеки лениво, поэтому «модель загрузилась»
    ещё не значит, что инференс пойдёт. При ошибке GPU перезагружаем модель
    на CPU/int8 и повторяем: задача выполняется, просто медленнее.
    """
    global _active_device, _active_compute_type
    for attempt in (0, 1):
        model = get_whisper_model(model_size)
        try:
            segments_gen, info = model.transcribe(input_path, **transcribe_kwargs)
            for seg in segments_gen:
                on_segment(seg)
            return info
        except Exception as exc:
            if attempt or _active_device != 'cuda' or not _looks_like_cuda_error(exc):
                raise
            logger.warning(f"GPU-инференс недоступен ({exc}) - повторяю на CPU/int8")
            _active_device, _active_compute_type = 'cpu', 'int8'
            with _model_lock:
                _model_cache.pop(model_size, None)
    raise RuntimeError('Транскрибация не удалась')


def _looks_like_cuda_error(exc):
    """Отличает проблему GPU-окружения от ошибки самого аудио/модели."""
    text = str(exc).lower()
    return any(marker in text for marker in ('cublas', 'cudnn', 'cuda', 'gpu', 'nvidia'))


def _load_whisper(whisper_model_cls, model_path, local_files, size):
    """Загружает модель; при проблемах с CUDA откатывается на CPU/int8.

    На машине с драйвером NVIDIA, но без CUDA-библиотек ctranslate2 загрузка
    модели падала бы навсегда - теперь задача всё равно выполнится (медленнее).
    """
    global _active_device, _active_compute_type
    try:
        return whisper_model_cls(model_path, device=_active_device,
                                 compute_type=_active_compute_type,
                                 local_files_only=local_files)
    except Exception as exc:
        if _active_device != 'cuda':
            raise
        logger.warning(f"CUDA недоступна для Whisper '{size}' ({exc}) - переключаюсь на CPU/int8")
        _active_device, _active_compute_type = 'cpu', 'int8'
        return whisper_model_cls(model_path, device='cpu', compute_type='int8',
                                 local_files_only=local_files)


def get_whisper_model(size=None):
    """Ленивая загрузка Whisper-модели нужного размера с кэшированием.

    Локальная папка models/<size> используется первой, иначе модель качается
    с HuggingFace автоматически - конфиги руками трогать не нужно.
    """
    global model_error
    size = size or WHISPER_MODEL_SIZE
    with _model_lock:
        if size in _model_cache:
            return _model_cache[size]
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            model_error = f"faster-whisper не установлен: {e}"
            raise RuntimeError(model_error) from e

        local_path = os.path.join(MODEL_DIR, size)
        if os.path.exists(local_path):
            model_path, local_files = local_path, True
            logger.info(f"Loading local Whisper '{size}' from {model_path} ({_device}/{_compute_type})")
        else:
            model_path, local_files = size, False
            logger.info(f"Whisper '{size}' отсутствует локально - скачиваю с HuggingFace")
        try:
            m = _load_whisper(WhisperModel, model_path, local_files, size)
        except Exception as e:
            model_error = str(e)
            logger.error(f"Не удалось загрузить Whisper '{size}': {e}")
            raise
        _model_cache[size] = m
        model_error = None
        return m


# Предзагрузка модели по умолчанию опциональна (PRELOAD_MODEL=1):
# по умолчанию сервер стартует мгновенно, модель грузится при первой задаче.
if os.environ.get('PRELOAD_MODEL', '0') == '1':
    try:
        get_whisper_model()
    except Exception as e:
        logger.warning(f"Предзагрузка модели не удалась: {e}")


def normalize_text(text):
    # Убираем все кроме букв и цифр, переводим в нижний регистр
    return re.sub(r'[^\w\s]', '', text).lower().strip()


def format_timestamp(seconds):
    seconds = max(0.0, float(seconds))
    total_ms = int(round(seconds * 1000))
    hours, rest_ms = divmod(total_ms, 3600_000)
    minutes, rest_ms = divmod(rest_ms, 60_000)
    secs, millis = divmod(rest_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def calculate_file_hash(file_path, sample_bytes=1024 * 1024):
    """Быстрый отпечаток файла: размер + первые и последние sample_bytes.

    Полное чтение 2-гигабайтного файла занимало секунды на каждой задаче;
    для кэша транскриптов такого отпечатка достаточно.
    """
    size = os.path.getsize(file_path)
    hash_md5 = hashlib.md5(str(size).encode())
    with open(file_path, "rb") as f:
        hash_md5.update(f.read(sample_bytes))
        if size > sample_bytes * 2:
            f.seek(-sample_bytes, os.SEEK_END)
            hash_md5.update(f.read(sample_bytes))
    return hash_md5.hexdigest()


def create_srt(segments, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments):
            start = format_timestamp(segment['start'])
            end = format_timestamp(segment['end'])
            text = segment['text'].strip()
            f.write(f"{i+1}\n{start} --> {end}\n{text}\n\n")


def create_txt(segments, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        full_text = " ".join([seg['text'].strip() for seg in segments])
        f.write(full_text)


def create_highlight_srt(segments, matches, output_path):
    """SRT с подсветкой найденных слов (HTML-теги <font>, поддерживаются плеерами)."""
    words = sorted({normalize_text(m['word']) for m in matches if normalize_text(m['word'])}, key=len, reverse=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments):
            text = segment['text'].strip()
            for w in words:
                text = re.sub(rf'(?<!\w){re.escape(w)}(?!\w)', r'<font color="#ef4444">\g<0></font>', text, flags=re.IGNORECASE)
            f.write(f"{i+1}\n{format_timestamp(segment['start'])} --> {format_timestamp(segment['end'])}\n{text}\n\n")


def create_highlight_txt(segments, matches, output_path):
    """TXT с найденными словами, обёрнутыми в 【 】."""
    words = sorted({normalize_text(m['word']) for m in matches if normalize_text(m['word'])}, key=len, reverse=True)
    full_text = " ".join([seg['text'].strip() for seg in segments])
    for w in words:
        full_text = re.sub(rf'(?<!\w){re.escape(w)}(?!\w)', '【\\g<0>】', full_text, flags=re.IGNORECASE)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_text)


# --- CORE LOGIC ---

def get_transcript_and_matches(input_path, filename, target_words, task_id=None,
                               language=None, stem_match=False, model_size=None,
                               progress_start=0, progress_span=0):
    """
    Возвращает данные транскрипции и совпадения для одного файла
    в локальном времени (начинается с 0).
    """
    file_hash = calculate_file_hash(input_path)
    # Кэш зависит от языка и размера модели (иначе транскрипт может не совпасть)
    cache_name = file_hash
    if model_size:
        cache_name += f"_{model_size}"
    if language:
        cache_name += f"_{language}"
    cache_path = os.path.join(CACHE_FOLDER, f"{cache_name}.json")

    segments_data = []
    file_duration = 0.0

    if os.path.exists(cache_path):
        logger.info(f"Using cached transcript for {filename}")
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            segments_data = cached_data['segments']
            file_duration = cached_data.get('duration', get_duration(input_path))
    else:
        logger.info(f"Transcribing new file {filename}")
        file_duration = get_duration(input_path)
        transcribe_kwargs = {'word_timestamps': True}
        if language:
            transcribe_kwargs['language'] = language

        def _collect(seg):
            # Реальный прогресс транскрибации (по времени обработанных сегментов)
            if task_id and progress_span and file_duration:
                pct = progress_start + int((seg.end / file_duration) * progress_span)
                time_code = f"{int(seg.end // 60)}:{int(seg.end % 60):02d}"
                update_job(task_id, f"Транскрибация… {time_code}", pct,
                           status_key='progress.transcribe', status_vars={'time': time_code})
            words_list = []
            if seg.words:
                for w in seg.words:
                    words_list.append({
                        'word': w.word,
                        'start': w.start,
                        'end': w.end
                    })
            segments_data.append({
                'start': seg.start,
                'end': seg.end,
                'text': seg.text,
                'words': words_list
            })

        info = _run_transcription(input_path, transcribe_kwargs, model_size or WHISPER_MODEL_SIZE, _collect)
        if info.duration:
            file_duration = info.duration

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({'duration': file_duration, 'segments': segments_data}, f, ensure_ascii=False)

    matches = []
    full_transcript = []
    found_words_list = []
    target_words_set = set(target_words)
    stems = [t for t in target_words_set if len(t) >= 3] if stem_match else []

    for segment in segments_data:
        full_transcript.append({'start': segment['start'], 'end': segment['end'], 'text': segment['text']})
        seg_words = segment['words']
        for wi, word in enumerate(seg_words):
            w_clean = normalize_text(word['word'])
            if stem_match:
                hit = any(w_clean.startswith(t) for t in stems)
            else:
                hit = w_clean in target_words_set
            if hit:
                # Контекст: ±3 слова вокруг найденного (для отображения в результатах)
                ctx = ' '.join(sw['word'] for sw in seg_words[max(0, wi - 3): wi + 4])
                matches.append({'start': word['start'], 'end': word['end'], 'word': word['word'], 'context': ctx})
                found_words_list.append(w_clean)

    word_counts = dict(Counter(found_words_list))
    return segments_data, matches, full_transcript, word_counts, file_duration
