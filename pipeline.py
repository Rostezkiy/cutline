"""Полный цикл обработки задачи (несколько файлов)."""

import gc
import os
import shutil
import subprocess
import uuid

from config import OUTPUT_FOLDER, TEMP_FOLDER, ffmpeg_path, logger
from jobstore import JobCancelled, _wait_while_paused, fail_job, finish_job, is_cancelled, job_slots, update_job
from media import cleanup_temp, process_single_file_to_temp
from summarize import summarize_transcript
from transcribe import create_highlight_srt, create_highlight_txt, create_srt, create_txt, get_transcript_and_matches


def process_task_multiple(task_id, input_paths, filenames, target_words, mode, settings):
    try:
        if is_cancelled(task_id):
            fail_job(task_id, 'Отменено пользователем', cancelled=True)
            return
        update_job(task_id, "В очереди...", 2, status_key='progress.queued')
        # Учитываем паузу очереди (/api/queue/pause) до захвата слота
        if not _wait_while_paused(task_id):
            return
        with job_slots:
            if is_cancelled(task_id):
                fail_job(task_id, 'Отменено пользователем', cancelled=True)
                return

            update_job(task_id, "Обработка списка файлов...", 5, status_key='progress.list')

            all_segments = []
            all_matches = []
            all_full_transcript = []
            all_word_counts = {}

            # Переменная для подсчета сдвига времени для ОБЩЕГО SRT
            total_offset_accumulator = 0.0

            processed_files = []
            is_video_input_global = any(f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')) for f in filenames)

            # Создаем временную директорию
            task_temp_dir = os.path.join(TEMP_FOLDER, task_id)
            os.makedirs(task_temp_dir, exist_ok=True)

            total_files = len(input_paths)

            # --- ЭТАП 1: Обработка каждого файла по отдельности ---
            for idx, (input_path, filename) in enumerate(zip(input_paths, filenames)):
                if is_cancelled(task_id):
                    raise JobCancelled()
                update_job(task_id, f"Файл {idx+1}/{total_files}: Анализ и обработка...",
                           10 + int(80 * idx / total_files),
                           status_key='progress.file', status_vars={'i': idx + 1, 'n': total_files})

                # 1. Получаем чистые данные (время начинается с 0)
                span = int(80 / total_files)
                segments, matches, full_trans, w_counts, duration = get_transcript_and_matches(
                    input_path, filename, target_words,
                    task_id=task_id,
                    language=settings.get('language'),
                    stem_match=settings.get('stem_match', False),
                    model_size=settings.get('model_size'),
                    progress_start=10 + int(80 * idx / total_files),
                    progress_span=span
                )

                # 2. Собираем статистику для итогового отчета (добавляем Offset только сюда!)
                for seg in segments:
                    seg_copy = seg.copy()
                    seg_copy['start'] += total_offset_accumulator
                    seg_copy['end'] += total_offset_accumulator
                    all_segments.append(seg_copy)

                for m in matches:
                    m_copy = m.copy()
                    m_copy['start'] += total_offset_accumulator
                    m_copy['end'] += total_offset_accumulator
                    all_matches.append(m_copy)

                for ft in full_trans:
                    ft_copy = ft.copy()
                    ft_copy['start'] += total_offset_accumulator
                    ft_copy['end'] += total_offset_accumulator
                    all_full_transcript.append(ft_copy)

                for w, c in w_counts.items():
                    all_word_counts[w] = all_word_counts.get(w, 0) + c

                # 3. Физическая обработка файла (передаем ЧИСТЫЕ matches без офсета)
                # В режиме summarize нарезку делать не нужно
                if mode != 'summarize':
                    temp_file_path = process_single_file_to_temp(
                        input_path, filename, matches, duration, mode, settings, task_id, task_temp_dir
                    )
                    if temp_file_path:
                        processed_files.append(temp_file_path)

                # Увеличиваем общий счетчик времени на длительность ОРИГИНАЛЬНОГО файла
                total_offset_accumulator += duration

            # --- ЭТАП 2: Генерация результатов ---

            base_name = f"result_{uuid.uuid4().hex[:6]}"

            # 1. Если режим сводки (Summarize)
            if mode == 'summarize':
                update_job(task_id, "Генерация сводки...", 90, status_key='progress.summary')
                summary_text = summarize_transcript(all_segments)
                summary_filename = f"{base_name}_summary.txt"
                with open(os.path.join(OUTPUT_FOLDER, summary_filename), 'w', encoding='utf-8') as f:
                    f.write(summary_text)

                # Также создаем SRT исходника
                create_srt(all_segments, os.path.join(OUTPUT_FOLDER, f"{base_name}.srt"))
                create_txt(all_segments, os.path.join(OUTPUT_FOLDER, f"{base_name}.txt"))

                finish_job(task_id,
                           download_url=f"/download/{summary_filename}",
                           report_url=f"/report/{task_id}",
                           summary_text=summary_text,
                           match_count=len(all_matches),
                           is_video=False,
                           filename=summary_filename,
                           srt_url=f"/download/{base_name}.srt",
                           txt_url=f"/download/{base_name}.txt",
                           matches_list=all_matches,
                           full_transcript=all_full_transcript,
                           word_counts=all_word_counts)
                gc.collect()
                return

            # 2. Склейка файлов (Concat)
            update_job(task_id, "Финальная склейка файлов...", 95, status_key='progress.concatAll')

            output_ext = settings.get('format', 'mp3')
            final_ext = output_ext
            if is_video_input_global and output_ext == 'mp4':
                final_ext = 'mp4'

            output_filename = f"{base_name}_cut.{final_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)

            if not processed_files:
                # Если файлов нет (например, save mode и ничего не нашлось) - понятная ошибка вместо тишины
                raise RuntimeError(
                    f"Совпадений не найдено ни в одном файле (режим {mode}). "
                    f"Проверьте список слов или включите поиск по основе слова.")
            elif len(processed_files) == 1:
                shutil.move(processed_files[0], output_path)
            else:
                # Concat через ffmpeg list
                concat_list_path = os.path.join(task_temp_dir, "concat_list_final.txt")
                with open(concat_list_path, 'w', encoding='utf-8') as f:
                    for pf in processed_files:
                        f.write(f"file '{os.path.abspath(pf)}'\n")

                subprocess.run(
                    [ffmpeg_path(), '-y', '-f', 'concat', '-safe', '0', '-i', concat_list_path, '-c', 'copy', output_path],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

            # Создание SRT/TXT + версии с подсветкой найденных слов
            srt_filename = f"{base_name}.srt"
            txt_filename = f"{base_name}.txt"
            hl_srt_filename = f"{base_name}_highlight.srt"
            hl_txt_filename = f"{base_name}_highlight.txt"
            create_srt(all_segments, os.path.join(OUTPUT_FOLDER, srt_filename))
            create_txt(all_segments, os.path.join(OUTPUT_FOLDER, txt_filename))
            create_highlight_srt(all_segments, all_matches, os.path.join(OUTPUT_FOLDER, hl_srt_filename))
            create_highlight_txt(all_segments, all_matches, os.path.join(OUTPUT_FOLDER, hl_txt_filename))

            finish_job(task_id,
                       download_url=f"/download/{output_filename}",
                       srt_url=f"/download/{srt_filename}",
                       txt_url=f"/download/{txt_filename}",
                       highlight_srt_url=f"/download/{hl_srt_filename}",
                       highlight_txt_url=f"/download/{hl_txt_filename}",
                       report_url=f"/report/{task_id}",
                       filename=output_filename,
                       match_count=len(all_matches),
                       is_video=final_ext == 'mp4',  # Тип плеера по фактическому выходному формату
                       matches_list=all_matches,
                       full_transcript=all_full_transcript,
                       word_counts=all_word_counts)
            gc.collect()

    except JobCancelled:
        logger.info(f"Task {task_id} cancelled by user")
        fail_job(task_id, 'Отменено пользователем', cancelled=True)
    except Exception as e:
        logger.error(f"Error in multi-file task {task_id}: {e}", exc_info=True)
        fail_job(task_id, str(e))
    finally:
        cleanup_temp(task_id)
        # Удаляем загруженные файлы после обработки (экономия места)
        for p in input_paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
        gc.collect()
