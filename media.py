"""Работа с ffmpeg: длительность, конвертация, нарезка, скачивание."""

import gc
import os
import shutil
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor

from pydub import AudioSegment
from pydub.generators import Sine

from config import MAX_WORKERS, TEMP_FOLDER, ffmpeg_path, ffprobe_path, logger
from jobstore import JobCancelled, is_cancelled, update_job


def cleanup_temp(unique_id):
    target_dir = os.path.join(TEMP_FOLDER, unique_id)
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir)
        except Exception as e:
            logger.error(f"Failed to cleanup temp {target_dir}: {e}")


def get_duration(file_path):
    try:
        cmd = [ffprobe_path(), '-v', 'error', '-show_entries', 'format=duration',
               '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        return float(subprocess.check_output(cmd).decode().strip())
    except Exception as e:
        logger.warning(f"Не удалось определить длительность {file_path}: {e}")
        return 0.0


def convert_to_format(input_path, output_path, output_ext):
    """
    Конвертирует файл целиком, если слов не найдено.
    Важно: ffmpeg корректно переделает видео в аудио (mp3), если требуется.
    """
    logger.info(f"Converting full file {input_path} to {output_path}")
    cmd = [ffmpeg_path(), '-y', '-i', input_path]
    # Маппинг расширение -> кодек (раньше для OGG/FLAC/WAV использовался AAC -> битые файлы)
    codec_map = {
        'mp3': ['-vn', '-acodec', 'libmp3lame', '-q:a', '2'],
        'wav': ['-vn', '-acodec', 'pcm_s16le'],
        'ogg': ['-vn', '-acodec', 'libvorbis', '-q:a', '5'],
        'flac': ['-vn', '-acodec', 'flac'],
        'mp4': ['-c:v', 'copy', '-c:a', 'aac'],  # Просто копируем потоки
    }
    cmd.extend(codec_map.get(output_ext, ['-vn', '-acodec', 'libmp3lame', '-q:a', '2']))
    cmd.append(output_path)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --- MEDIA PROCESSING ---

def merge_intervals(matches, gap=0.0):
    """Объединяет перекрывающиеся/близкие интервалы (не меняя входные словари)."""
    ordered = sorted(matches, key=lambda x: x['start'])
    merged = []
    for m in ordered:
        if merged and m['start'] <= merged[-1]['end'] + gap:
            merged[-1]['end'] = max(merged[-1]['end'], m['end'])
        else:
            merged.append({'start': m['start'], 'end': m['end']})
    return merged


def calculate_keep_segments(matches, total_duration, mode):
    # Сортируем и объединяем перекрывающиеся интервалы удаления
    matches = merge_intervals(matches)

    segments = []
    if mode == 'save':
        segments = [(m['start'], m['end']) for m in matches]
    elif mode == 'remove' or mode == 'cut':
        current_time = 0.0
        for m in matches:
            if m['start'] > current_time:
                segments.append((current_time, m['start']))
            current_time = max(current_time, m['end'])

        # Добавляем хвост, если он есть
        if current_time < total_duration:
            segments.append((current_time, total_duration))

    # Фильтруем мусор < 0.1 сек
    return [s for s in segments if (s[1] - s[0]) > 0.1]


def process_replace_chunked(input_path, output_path, matches, is_video, settings, task_id, total_duration, out_ext='mp3'):
    # Для mp4-выхода работаем через mp3-временный файл, иначе - в целевом формате (иначе битый контейнер)
    work_ext = 'mp3' if (is_video and out_ext == 'mp4') else out_ext
    temp_audio_out = os.path.join(TEMP_FOLDER, task_id, f"replaced_audio.{work_ext}")
    freq = int(settings.get('beep_freq', 1000))
    gain = int(settings.get('beep_gain', -10))
    mute = bool(settings.get('mute'))  # Режим "mute": тишина вместо бипа (длительность сохраняется)

    # Перекрывающиеся совпадения (и паддинг) склеиваем, иначе бип добавляется
    # повторно и длительность аудио уезжает (рассинхрон видео/аудио).
    matches = merge_intervals(matches)
    chunk_files = []
    current_pos = 0.0
    chunk_idx = 0
    matches_ms = [{'start': int(m['start']*1000), 'end': int(m['end']*1000)} for m in matches]
    CHUNK_SIZE_SEC = 600

    while current_pos < total_duration:
        if is_cancelled(task_id):
            raise JobCancelled()
        chunk_end = min(current_pos + CHUNK_SIZE_SEC, total_duration)
        percent = 50 + int((current_pos / total_duration) * 40)
        update_job(task_id, f"Обработка аудио: {int(current_pos//60)} мин...", percent,
                   status_key='progress.audio', status_vars={'min': int(current_pos // 60)})

        t_start = current_pos
        t_dur = chunk_end - current_pos

        # Загружаем кусок
        audio_chunk = AudioSegment.from_file(input_path, start_second=t_start, duration=t_dur)
        chunk_start_ms = int(t_start * 1000)
        chunk_end_ms = int(chunk_end * 1000)
        local_matches = [m for m in matches_ms if m['end'] > chunk_start_ms and m['start'] < chunk_end_ms]

        if local_matches:
            processed_chunk = AudioSegment.empty()
            last_idx_in_chunk = 0
            for m in local_matches:
                m_start_rel = max(0, m['start'] - chunk_start_ms)
                m_end_rel = min(len(audio_chunk), m['end'] - chunk_start_ms)
                if m_start_rel > last_idx_in_chunk:
                    processed_chunk += audio_chunk[last_idx_in_chunk:m_start_rel]
                beep_dur = m_end_rel - m_start_rel
                if beep_dur > 0:
                    if mute:
                        processed_chunk += AudioSegment.silent(duration=beep_dur)
                    else:
                        beep = Sine(freq).to_audio_segment(duration=beep_dur).apply_gain(gain)
                        processed_chunk += beep
                last_idx_in_chunk = m_end_rel
            if last_idx_in_chunk < len(audio_chunk):
                processed_chunk += audio_chunk[last_idx_in_chunk:]
            audio_chunk = processed_chunk

        part_filename = os.path.join(TEMP_FOLDER, task_id, f"part_{chunk_idx:04d}.{work_ext}")
        audio_chunk.export(part_filename, format=work_ext)
        chunk_files.append(part_filename)
        del audio_chunk
        gc.collect()
        current_pos = chunk_end
        chunk_idx += 1

    concat_list_path = os.path.join(TEMP_FOLDER, task_id, "concat_list.txt")
    with open(concat_list_path, 'w') as f:
        for cf in chunk_files:
            f.write(f"file '{os.path.abspath(cf)}'\n")

    subprocess.run([ffmpeg_path(), '-y', '-f', 'concat', '-safe', '0', '-i', concat_list_path, '-c', 'copy', temp_audio_out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if is_video and output_path.endswith('.mp4'):
        update_job(task_id, "Сборка видео...", 95, status_key='progress.video')
        # Копируем видео, заменяем аудио
        cmd = [ffmpeg_path(), '-y', '-i', input_path, '-i', temp_audio_out, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest', output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # Если выход нужен mp3 (даже если вход видео), просто отдаем аудио
        shutil.move(temp_audio_out, output_path)


def parallel_media_cut(input_path, output_path, segments, is_video_input, task_id, ext, accurate=True):
    """Нарезка/склейка по сегментам.

    accurate=True - точный seek (медленнее, но границы точные): -ss ставится
    после -i вместе с -accurate_seek. accurate=False - быстрый seek до -i.
    """
    if not segments:
        return

    task_dir = os.path.join(TEMP_FOLDER, task_id)
    chunk_files = [None] * len(segments)

    # Определяем нужные кодеки
    # Если на выходе MP4: видео перекодируем (для точности стыков), аудио AAC
    # Если на выходе MP3: видео отбрасываем, аудио MP3

    def process_one_segment(index, start, end):
        duration = end - start
        chunk_name = f"chunk_{index:04d}.{ext}"
        chunk_path = os.path.join(task_dir, chunk_name)

        if accurate:
            # Точный seek: -ss после -i + -accurate_seek (медленнее, без сдвига границ)
            cmd = [ffmpeg_path(), '-y', '-accurate_seek', '-i', input_path,
                   '-ss', f"{start:.3f}", '-t', f"{duration:.3f}"]
        else:
            # Быстрый seek (-ss перед -i)
            cmd = [ffmpeg_path(), '-y', '-ss', f"{start:.3f}", '-t', f"{duration:.3f}", '-i', input_path]

        if ext == 'mp4':
            # Перекодирование x264 ultrafast для скорости
            cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-c:a', 'aac'])
        else:
            # Только аудио: кодек по расширению (раньше всегда mp3 -> битые wav/ogg/flac)
            codec_map = {
                'wav': ['-vn', '-acodec', 'pcm_s16le'],
                'ogg': ['-vn', '-acodec', 'libvorbis', '-q:a', '5'],
                'flac': ['-vn', '-acodec', 'flac'],
            }
            cmd.extend(codec_map.get(ext, ['-vn', '-c:a', 'libmp3lame', '-q:a', '2']))

        cmd.append(chunk_path)

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return (index, chunk_path)
        except Exception as e:
            logger.error(f"Error cutting segment {index}: {e}")
            return (index, None)

    total_segs = len(segments)
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i, (s, e) in enumerate(segments):
            if is_cancelled(task_id):
                raise JobCancelled()
            futures.append(executor.submit(process_one_segment, i, s, e))

        for future in futures:
            if is_cancelled(task_id):
                raise JobCancelled()
            idx, path = future.result()
            completed += 1
            if completed % 5 == 0 or completed == total_segs:
                percent = 50 + int((completed / total_segs) * 45)
                update_job(task_id, f"Нарезка: {completed}/{total_segs}", percent,
                           status_key='progress.cut', status_vars={'done': completed, 'total': total_segs})

            chunk_files[idx] = path

    valid_chunks = [f for f in chunk_files if f is not None]
    if not valid_chunks:
        raise Exception("Failed to create chunks")

    update_job(task_id, "Финальная склейка...", 98, status_key='progress.concat')
    concat_list_path = os.path.join(task_dir, "final_concat_list.txt")
    with open(concat_list_path, 'w') as f:
        for cf in valid_chunks:
            f.write(f"file '{os.path.abspath(cf)}'\n")

    subprocess.run([ffmpeg_path(), '-y', '-f', 'concat', '-safe', '0', '-i', concat_list_path, '-c', 'copy', output_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --- SINGLE FILE PROCESSING ---
def process_single_file_to_temp(input_path, filename, matches, duration, mode, settings, task_id, temp_dir):

    """
    Обрабатывает один файл на основе переданных matches.
    Возвращает путь к временному файлу или None.
    """
    is_video_input = filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))
    output_ext = settings.get('format', 'mp3')
    final_ext = output_ext
    if is_video_input and output_ext == 'mp4':
        final_ext = 'mp4'

    padding_sec = int(settings.get('padding', 0)) / 1000.0

    # Добавляем паддинг к совпадениям
    processed_matches = []
    for m in matches:
        processed_matches.append({
            'start': max(0, m['start'] - padding_sec),
            'end': min(duration, m['end'] + padding_sec)
        })

    # Логика режимов
    # 1. Если совпадений нет
    if not processed_matches:
        if mode == 'save':
            # Режим "сохранить слова", но слов нет -> файл пропускаем
            return None
        else:
            # Режимы remove/replace/cut, но слов нет -> оставляем файл как есть (просто конвертируем)
            temp_output = os.path.join(temp_dir, f"full_{uuid.uuid4().hex[:6]}.{final_ext}")
            convert_to_format(input_path, temp_output, final_ext)
            return temp_output

    # 2. Режим replace (запикивание / mute)
    if mode == 'replace':
        temp_output = os.path.join(temp_dir, f"replaced_{uuid.uuid4().hex[:6]}.{final_ext}")
        process_replace_chunked(input_path, temp_output, processed_matches, is_video_input, settings, task_id, duration, final_ext)
        return temp_output

    # 3. Режимы remove / save / cut
    keep_segments = calculate_keep_segments(processed_matches, duration, mode)

    if not keep_segments:
        # Если удалено вообще всё -> создаем тишину 1 сек, чтобы не ломать склейку
        temp_output = os.path.join(temp_dir, f"silence_{uuid.uuid4().hex[:6]}.{final_ext}")
        AudioSegment.silent(duration=1000).export(temp_output, format=final_ext)
        return temp_output

    temp_output = os.path.join(temp_dir, f"cut_{uuid.uuid4().hex[:6]}.{final_ext}")
    parallel_media_cut(input_path, temp_output, keep_segments, is_video_input, task_id, final_ext,
                       accurate=bool(settings.get('accurate_cut', True)))
    return temp_output


def download_from_url(url, dest_dir):
    """Скачивает медиа по ссылке (YouTube и др.) через yt-dlp."""
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp не установлен. Установите: pip install yt-dlp")

    outtmpl = os.path.join(dest_dir, '%(id)s.%(ext)s')
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            if not os.path.exists(path):
                # Расширение могло измениться - ищем по id
                candidates = [os.path.join(dest_dir, f) for f in os.listdir(dest_dir)
                              if f.startswith(info.get('id', '') or '')]
                if not candidates:
                    raise RuntimeError("Не удалось определить скачанный файл")
                path = candidates[0]
            return path, info.get('title') or os.path.basename(path)
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Ошибка скачивания по ссылке: {e}")
