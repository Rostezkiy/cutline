"""Пресеты в файлах и ZIP-экспорт результатов (Blueprint `/api`).

Пресеты больше не живут в localStorage браузера: они хранятся в
presets.json рядом с данными программы, поэтому переносятся между
браузерами/машинами и участвуют в экспорте/импорте.

Роуты:
    GET    /api/presets               - список пресетов
    POST   /api/presets               - сохранить пресет
    DELETE /api/presets/<name>        - удалить пресет
    GET    /api/presets/export        - выгрузка пресетов в JSON-файл
    POST   /api/presets/import        - импорт пресетов
    GET    /api/export/<task_id>      - ZIP с результатами задачи
"""

import json
import logging
import os
import tempfile
import threading
import zipfile

from flask import Blueprint, jsonify, request, send_file

MAX_PRESETS = 200
MAX_WORDS = 500
MAX_WORD_LEN = 64
ALLOWED_SETTING_KEYS = {
    'mode', 'padding', 'freq', 'gain', 'format', 'language', 'model_size', 'stem', 'mute',
}
JOB_URL_FIELDS = ('download_url', 'srt_url', 'txt_url', 'highlight_srt_url', 'highlight_txt_url')


def _clean_words(value):
    words = []
    for item in value or []:
        if not isinstance(item, (str, int, float)):
            continue
        word = str(item).strip()[:MAX_WORD_LEN]
        if word:
            words.append(word)
        if len(words) >= MAX_WORDS:
            break
    return words


def _clean_settings(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, raw in value.items():
        if key not in ALLOWED_SETTING_KEYS:
            continue
        if isinstance(raw, bool) or isinstance(raw, (int, float)):
            result[key] = raw
        elif isinstance(raw, str):
            result[key] = raw[:64]
    return result


def _clean_name(name):
    name = str(name or '').strip().replace('\\', '/')
    name = name.split('/')[-1][:60]
    return name


def create_blueprint(*, output_dir, presets_path, job_provider, logger=None):
    """Создаёт Blueprint пресетов и экспорта.

    job_provider - функция (task_id) -> dict задачи или None.
    """
    log = logger or logging.getLogger(__name__)
    lock = threading.Lock()
    os.makedirs(os.path.dirname(presets_path) or '.', exist_ok=True)
    bp = Blueprint('files_api', __name__)

    # --- пресеты ---

    def _read_presets():
        try:
            with open(presets_path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return {}
        except Exception as exc:  # noqa: BLE001 - битый файл не должен ломать UI
            log.error(f"Не удалось прочитать пресеты: {exc}")
            return {}
        if not isinstance(data, dict):
            return {}
        result = {}
        for name, entry in data.items():
            cleaned_name = _clean_name(name)
            if not cleaned_name:
                continue
            if isinstance(entry, list):
                result[cleaned_name] = {'words': _clean_words(entry), 'settings': {}}
            elif isinstance(entry, dict):
                result[cleaned_name] = {'words': _clean_words(entry.get('words')),
                                        'settings': _clean_settings(entry.get('settings'))}
        return result

    def _write_presets(presets):
        tmp_path = f"{presets_path}.tmp"
        with open(tmp_path, 'w', encoding='utf-8') as fh:
            json.dump(presets, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, presets_path)

    @bp.route('/api/presets')
    def list_presets():
        with lock:
            presets = _read_presets()
        return jsonify({'presets': presets, 'count': len(presets), 'path': presets_path})

    @bp.route('/api/presets', methods=['POST'])
    def save_preset():
        payload = request.get_json(silent=True) or {}
        name = _clean_name(payload.get('name'))
        if not name:
            return jsonify({'error': 'Укажите название пресета'}), 400
        entry = payload.get('entry')
        if isinstance(entry, list):
            words, settings = _clean_words(entry), {}
        elif isinstance(entry, dict):
            words = _clean_words(entry.get('words'))
            settings = _clean_settings(entry.get('settings'))
        else:
            words = _clean_words(payload.get('words'))
            settings = _clean_settings(payload.get('settings'))
        if not words:
            return jsonify({'error': 'Список слов пуст'}), 400
        with lock:
            presets = _read_presets()
            if name not in presets and len(presets) >= MAX_PRESETS:
                return jsonify({'error': f'Слишком много пресетов (лимит {MAX_PRESETS})'}), 400
            presets[name] = {'words': words, 'settings': settings}
            _write_presets(presets)
        return jsonify({'success': True, 'name': name, 'presets': presets})

    @bp.route('/api/presets/<name>', methods=['DELETE'])
    def delete_preset(name):
        name = _clean_name(name)
        with lock:
            presets = _read_presets()
            if name not in presets:
                return jsonify({'error': 'Пресет не найден'}), 404
            del presets[name]
            _write_presets(presets)
        return jsonify({'success': True, 'presets': presets})

    @bp.route('/api/presets/export')
    def export_presets():
        with lock:
            presets = _read_presets()
        response = jsonify({'version': 1, 'presets': presets})
        response.headers['Content-Disposition'] = 'attachment; filename=cutline_presets.json'
        return response

    @bp.route('/api/presets/import', methods=['POST'])
    def import_presets():
        payload = request.get_json(silent=True) or {}
        if 'presets' in payload:
            incoming = payload['presets']
            if not isinstance(incoming, dict):
                return jsonify({'error': 'Ожидается JSON с пресетами'}), 400
        else:
            incoming = payload
        if not isinstance(incoming, dict):
            return jsonify({'error': 'Ожидается JSON с пресетами'}), 400
        added = 0
        with lock:
            presets = _read_presets()
            for raw_name, entry in incoming.items():
                if raw_name == 'version':
                    continue
                name = _clean_name(raw_name)
                if not name:
                    continue
                if isinstance(entry, list):
                    words, settings = _clean_words(entry), {}
                elif isinstance(entry, dict):
                    words = _clean_words(entry.get('words'))
                    settings = _clean_settings(entry.get('settings'))
                else:
                    continue
                if not words:
                    continue
                presets[name] = {'words': words, 'settings': settings}
                added += 1
            _write_presets(presets)
        return jsonify({'success': True, 'imported': added, 'presets': presets})

    # --- ZIP-экспорт ---

    def _job_file_names(job):
        names = []
        for field in JOB_URL_FIELDS:
            url = job.get(field) or ''
            if '/download/' not in url:
                continue
            name = os.path.basename(url.split('/download/', 1)[1])
            if name and name not in names:
                names.append(name)
        return names

    def _build_report(job, task_id):
        report = {
            'task_id': task_id,
            'created_at': job.get('created_at'),
            'finished_at': job.get('finished_at'),
            'mode': job.get('mode'),
            'filenames': job.get('filenames'),
            'words': job.get('words'),
            'match_count': job.get('match_count'),
            'word_counts': job.get('word_counts'),
            'matches': job.get('matches_list'),
            'output': job.get('filename'),
        }
        return json.dumps(report, ensure_ascii=False, indent=2)

    def _readme(job, task_id):
        lines = [
            'Cutline export',
            'task: %s' % task_id,
            'mode: %s' % job.get('mode'),
            'files: %s' % ', '.join(job.get('filenames') or []),
            'matches: %s' % job.get('match_count'),
            '',
            'SRT/TXT - субтитры и текст, *_highlight - с подсветкой найденных слов.',
            'report.json - машинно-читаемый отчёт по задаче.',
        ]
        return '\n'.join(lines)

    @bp.route('/api/export/<task_id>')
    def export_zip(task_id):
        job = job_provider(task_id)
        if not job:
            return jsonify({'error': 'Задача не найдена'}), 404
        if job.get('status') != 'completed':
            return jsonify({'error': 'Задача не завершена'}), 400
        handler, temp_path = tempfile.mkstemp(suffix='.zip', prefix='cutline_')
        os.close(handler)
        added = 0
        try:
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                for name in _job_file_names(job):
                    path = os.path.join(output_dir, name)
                    if not os.path.isfile(path):
                        continue
                    media = name.lower().endswith(('.mp3', '.mp4', '.wav', '.ogg', '.flac', '.mkv'))
                    archive.write(path, name, compress_type=zipfile.ZIP_STORED if media else zipfile.ZIP_DEFLATED)
                    added += 1
                archive.writestr('report.json', _build_report(job, task_id))
                archive.writestr('README.txt', _readme(job, task_id))
        except Exception as exc:  # noqa: BLE001
            log.error(f"Не удалось собрать ZIP для {task_id}: {exc}")
            try:
                os.remove(temp_path)
            except OSError:
                pass
            return jsonify({'error': f'Не удалось собрать архив: {exc}'}), 500
        if not added:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            return jsonify({'error': 'Файлы результата не найдены'}), 404
        download_name = f"cutline_{task_id[:8]}.zip"
        response = send_file(temp_path, as_attachment=True, download_name=download_name,
                             mimetype='application/zip')
        response.call_on_close(lambda: os.path.exists(temp_path) and os.remove(temp_path))
        return response

    return bp
