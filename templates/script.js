// ==================== I18N ====================
const I18N = {
    ru: {
        'nav.home': 'Главная', 'nav.settings': 'Настройки', 'nav.results': 'Результаты',
        'upload.hint': 'Перетащите файлы сюда или нажмите для выбора',
        'upload.supported': 'Аудио / видео, можно несколько файлов',
        'upload.or': 'или', 'upload.urlPh': 'Вставьте ссылку (YouTube)...',
        'upload.clear': 'Очистить всё',
        'tags.title': 'Фильтр слов', 'tags.placeholder': 'Введите слово и нажмите Enter...',
        'tags.clear': 'Очистить', 'tags.savePreset': 'Сохранить как пресет',
        'mode.remove': 'Удалить', 'mode.save': 'Изолировать', 'mode.replace': 'Запикать', 'mode.summarize': 'Пересказ',
        'stage.upload': 'Загрузка', 'stage.transcribe': 'Транскрибация', 'stage.analyze': 'Анализ',
        'stage.render': 'Рендер', 'stage.concat': 'Склейка', 'stage.cancel': 'Отменить',
        'startBtn': 'Начать обработку',
        'settings.general': 'Основные настройки', 'settings.padding': 'Отступ (мс)',
        'settings.format': 'Формат аудио', 'settings.language': 'Язык распознавания', 'settings.model': 'Модель Whisper',
        'settings.stem': 'Искать по основе слова (напр. «мат» найдёт «мата», «матом»)',
        'settings.beep': 'Настройки бипа', 'settings.freq': 'Частота (Гц)', 'settings.gain': 'Громкость (Gain)',
        'settings.mute': 'Заглушить тишиной вместо бипа (длительность сохраняется)',
        'settings.previewBeep': 'Прослушать звук', 'settings.presets': 'Пресеты', 'settings.presetName': 'Название пресета...',
        'history.title': 'История', 'history.empty': 'Задач пока нет', 'history.open': 'Открыть', 'history.download': 'Скачать',
        'results.empty': 'Результатов пока нет',
        'results.tab.matches': 'Совпадения', 'results.tab.statistics': 'Статистика',
        'results.tab.transcript': 'Полный текст', 'results.tab.summary': 'AI Пересказ',
        'results.col.time': 'Время', 'results.col.word': 'Слово', 'results.col.context': 'Контекст', 'results.col.count': 'Кол-во',
        'results.searchPh': 'Поиск по тексту...', 'results.copy': 'Копировать',
        'toast.uploadDone': 'Файлы загружены, запущена обработка',
        'toast.cancelled': 'Задача отменена', 'toast.copied': 'Скопировано в буфер обмена',
        'toast.noFile': 'Файл не выбран', 'toast.noWords': 'Список слов пуст',
        'toast.connError': 'Ошибка связи с сервером',
        'toast.ffmpegMissing': 'FFmpeg не найден — обработка медиа не будет работать',
        'toast.ollamaOffline': 'Ollama не запущена — режим «Пересказ» недоступен',
        'toast.modelNotLoaded': 'Модель «{model}» не загружена в Ollama',
        'status.init': 'Инициализация...',
        'settings.modelSmall': 'Small (быстро)', 'settings.modelMedium': 'Medium (баланс)',
        'settings.modelLarge': 'Large (точно)',
        'aria.sections': 'Разделы', 'aria.chooseFiles': 'Выбрать файлы',
        'aria.modeGroup': 'Режим обработки', 'aria.refreshModels': 'Обновить список моделей',
        'aria.savePreset': 'Сохранить пресет', 'aria.refresh': 'Обновить', 'aria.close': 'Закрыть',
        'progress.queued': 'В очереди...', 'progress.list': 'Обработка списка файлов...',
        'progress.file': 'Файл {i}/{n}: анализ и обработка...',
        'progress.summary': 'Генерация сводки...',
        'progress.concatAll': 'Финальная склейка файлов...',
        'progress.transcribe': 'Транскрибация… {time}',
        'progress.audio': 'Обработка аудио: {min} мин...', 'progress.video': 'Сборка видео...',
        'progress.cut': 'Нарезка: {done}/{total}', 'progress.concat': 'Финальная склейка...',
        'history.matches': 'совпадений: {n}',
    },
    en: {
        'nav.home': 'Home', 'nav.settings': 'Settings', 'nav.results': 'Results',
        'upload.hint': 'Drag & drop files or click to upload',
        'upload.supported': 'Audio / video, multiple files allowed',
        'upload.or': 'or', 'upload.urlPh': 'Paste a link (YouTube)...',
        'upload.clear': 'Clear all',
        'tags.title': 'Word Filter', 'tags.placeholder': 'Enter a word and press Enter...',
        'tags.clear': 'Clear All', 'tags.savePreset': 'Save as Preset',
        'mode.remove': 'Remove', 'mode.save': 'Isolate', 'mode.replace': 'Bleep', 'mode.summarize': 'Summary',
        'stage.upload': 'Upload', 'stage.transcribe': 'Transcribe', 'stage.analyze': 'Analyze',
        'stage.render': 'Render', 'stage.concat': 'Merge', 'stage.cancel': 'Cancel',
        'startBtn': 'Start Processing',
        'settings.general': 'General Settings', 'settings.padding': 'Padding (ms)',
        'settings.format': 'Audio Format', 'settings.language': 'Recognition language', 'settings.model': 'Whisper model',
        'settings.stem': 'Match by word stem (e.g. "мат" also finds "мата", "матом")',
        'settings.beep': 'Beep Settings', 'settings.freq': 'Frequency (Hz)', 'settings.gain': 'Volume (Gain)',
        'settings.mute': 'Mute instead of beep (silence, keeps duration)',
        'settings.previewBeep': 'Preview sound', 'settings.presets': 'Presets', 'settings.presetName': 'Preset name...',
        'history.title': 'History', 'history.empty': 'No tasks yet', 'history.open': 'Open', 'history.download': 'Download',
        'results.empty': 'No results available',
        'results.tab.matches': 'Matches', 'results.tab.statistics': 'Statistics',
        'results.tab.transcript': 'Full Transcript', 'results.tab.summary': 'AI Summary',
        'results.col.time': 'Timecode', 'results.col.word': 'Word', 'results.col.context': 'Context', 'results.col.count': 'Count',
        'results.searchPh': 'Search in transcript...', 'results.copy': 'Copy',
        'toast.uploadDone': 'Files uploaded, processing started',
        'toast.cancelled': 'Task cancelled', 'toast.copied': 'Copied to clipboard',
        'toast.noFile': 'No file selected', 'toast.noWords': 'Word list is empty',
        'toast.connError': 'Connection error',
        'toast.ffmpegMissing': 'FFmpeg not found — media processing will not work',
        'toast.ollamaOffline': 'Ollama is not running — summary mode is unavailable',
        'toast.modelNotLoaded': 'Model "{model}" is not loaded in Ollama',
        'status.init': 'Initializing...',
        'settings.modelSmall': 'Small (fast)', 'settings.modelMedium': 'Medium (balanced)',
        'settings.modelLarge': 'Large (accurate)',
        'aria.sections': 'Sections', 'aria.chooseFiles': 'Choose files',
        'aria.modeGroup': 'Processing mode', 'aria.refreshModels': 'Refresh model list',
        'aria.savePreset': 'Save preset', 'aria.refresh': 'Refresh', 'aria.close': 'Close',
        'progress.queued': 'Queued...', 'progress.list': 'Processing file list...',
        'progress.file': 'File {i}/{n}: analyzing and processing...',
        'progress.summary': 'Generating summary...',
        'progress.concatAll': 'Final concatenation...',
        'progress.transcribe': 'Transcribing… {time}',
        'progress.audio': 'Processing audio: {min} min...', 'progress.video': 'Building video...',
        'progress.cut': 'Cutting: {done}/{total}', 'progress.concat': 'Final concatenation...',
        'history.matches': 'matches: {n}',
    }
};
// Иконки: инлайн-SVG спрайт из index.html (без внешних CDN)
function iconEl(name, extra) {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('class', 'icon' + (extra ? ' ' + extra : ''));
    svg.setAttribute('aria-hidden', 'true');
    const use = document.createElementNS(ns, 'use');
    use.setAttribute('href', '#i-' + name);
    svg.appendChild(use);
    return svg;
}
function iconHtml(name, extra) {
    return '<svg class="icon' + (extra ? ' ' + extra : '') + '" aria-hidden="true"><use href="#i-' + name + '"></use></svg>';
}

let currentLang = localStorage.getItem('app_lang') || 'ru';
function t(key, vars) {
    const dict = I18N[currentLang] || {};
    let text = dict[key] || I18N.ru[key] || key;
    if (vars) text = String(text).replace(/\{(\w+)\}/g, (m, name) => (name in vars ? vars[name] : m));
    return text;
}
function applyLang() {
    document.documentElement.lang = currentLang;
    document.getElementById('btn-lang').textContent = currentLang.toUpperCase();
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
    if (typeof renderPresets === 'function') renderPresets();
    if (typeof loadHistory === 'function' && document.getElementById('view-results').classList.contains('active')) loadHistory();
}
function toggleLang() { currentLang = currentLang === 'ru' ? 'en' : 'ru'; localStorage.setItem('app_lang', currentLang); applyLang(); }

// ==================== THEME ====================
function initTheme() {
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
}
function toggleTheme() {
    if (document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.remove('dark'); localStorage.theme = 'light';
    } else {
        document.documentElement.classList.add('dark'); localStorage.theme = 'dark';
    }
}
initTheme();

// ==================== TOASTS ====================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const variant = ['info', 'success', 'error'].includes(type) ? type : 'info';
    const el = document.createElement('div');
    el.className = 'toast toast--' + variant;
    el.setAttribute('role', variant === 'error' ? 'alert' : 'status');
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.classList.add('is-leaving'), 3600);
    setTimeout(() => el.remove(), 4200);
}

// ==================== TABS ====================
function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.getElementById('view-' + tab).classList.add('active');

    document.querySelectorAll('.nav-btn').forEach(btn => {
        const isActive = btn.id === 'tab-' + tab;
        btn.classList.toggle('is-active', isActive);
        btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    if (tab === 'results') {
        document.getElementById('res-badge').classList.add('hidden');
        loadHistory();
    }
}
switchTab('home');
// Прямые ссылки на раздел: /#settings, /#results
function applyTabFromHash() {
    const tab = (location.hash || '').replace('#', '');
    if (['home', 'settings', 'results'].includes(tab)) switchTab(tab);
}
applyTabFromHash();
window.addEventListener('hashchange', applyTabFromHash);

function toggleResultView(view) {
    document.querySelectorAll('.res-view').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.res-tab').forEach(el => el.classList.remove('active'));
    document.getElementById('res-view-' + view).classList.remove('hidden');
    document.getElementById('res-tab-' + view).classList.add('active');
}

// ==================== TAGS TOGGLE ====================
function toggleTagsView() {
    const wrapper = document.getElementById('tags-wrapper');
    const chevron = document.getElementById('tags-toggle-icon');
    const fade = document.getElementById('tags-fade');
    const expanded = wrapper.classList.toggle('is-expanded');
    if (chevron) chevron.style.transform = expanded ? 'rotate(180deg)' : 'rotate(0deg)';
    if (fade) fade.classList.toggle('is-hidden', expanded);
}

// ==================== TAGS LOGIC ====================
let tags = [];
const tagInput = document.getElementById('tag-input');
const tagsContainer = document.getElementById('tags-container');
tagInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { addTags(e.target.value); e.target.value = ''; }
    else if (e.key === 'Backspace' && !e.target.value) { tags.pop(); renderTags(); }
});
function addTags(inputStr) {
    inputStr.split(/,| /).map(x => x.trim()).filter(x => x && !tags.includes(x)).forEach(val => tags.push(val));
    renderTags();
}

function persistTags() {
    try { localStorage.setItem('app_tags', JSON.stringify(tags)); } catch (e) { }
}

function renderTags() {
    persistTags();
    tagsContainer.innerHTML = '';
    tags.forEach(tag => {
        const el = document.createElement('div');
        el.className = 'chip';
        const span = document.createElement('span');
        span.textContent = tag;
        const btn = document.createElement('button');
        btn.className = 'chip__remove';
        btn.setAttribute('aria-label', 'Remove tag');
        btn.appendChild(iconEl('close'));
        btn.addEventListener('click', () => removeTag(tag));
        el.appendChild(span);
        el.appendChild(btn);
        tagsContainer.appendChild(el);
    });
}
function clearAllTags() {
    if (tags.length === 0) return;
    tags = [];
    renderTags();
    document.getElementById('tag-input').focus();
}
function removeTag(t) { tags = tags.filter(tag => tag !== t); renderTags(); }
function setTags(newTags) { tags = newTags; renderTags(); }

// ==================== FILES & DRAG&DROP ====================
let selectedFiles = [];
const fileInput = document.getElementById('file-input');
const dropzone = document.getElementById('upload-dropzone');

fileInput.addEventListener('change', () => { if (fileInput.files.length) addFiles(fileInput.files); });

['dragenter', 'dragover'].forEach(ev => dropzone.addEventListener(ev, (e) => {
    e.preventDefault(); e.stopPropagation(); dropzone.classList.add('dragging');
}));
['dragleave', 'drop'].forEach(ev => dropzone.addEventListener(ev, (e) => {
    e.preventDefault(); e.stopPropagation(); dropzone.classList.remove('dragging');
}));
dropzone.addEventListener('drop', (e) => { if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files); });

function addFiles(fileList) {
    Array.from(fileList).forEach(f => {
        if (!selectedFiles.some(x => x.name === f.name && x.size === f.size)) selectedFiles.push(f);
    });
    fileInput.value = '';
    renderFileList();
}
function removeFile(name, size) {
    selectedFiles = selectedFiles.filter(f => !(f.name === name && f.size === size));
    renderFileList();
}
function clearAllFiles() { selectedFiles = []; renderFileList(); }

function fmtSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function renderFileList() {
    const panel = document.getElementById('file-list-panel');
    const list = document.getElementById('file-list');
    list.innerHTML = '';
    if (!selectedFiles.length) {
        panel.classList.add('hidden');
        document.getElementById('upload-placeholder').classList.remove('hidden');
        return;
    }
    panel.classList.remove('hidden');
    document.getElementById('upload-placeholder').classList.add('hidden');

    let total = 0;
    selectedFiles.forEach(f => {
        total += f.size;
        const isVideo = f.type.startsWith('video') || f.name.match(/\.(mp4|mov|mkv|avi|webm)$/i);
        const row = document.createElement('div');
        row.className = 'list-row';
        const icon = iconEl(isVideo ? 'video' : 'audio', 'list-row__icon');
        const info = document.createElement('div');
        info.className = 'list-row__body';
        const name = document.createElement('p');
        name.className = 'list-row__title';
        name.textContent = f.name;
        const meta = document.createElement('p');
        meta.className = 'list-row__meta';
        meta.textContent = fmtSize(f.size);
        info.appendChild(name);
        info.appendChild(meta);
        const del = document.createElement('button');
        del.className = 'icon-btn list-row__action';
        del.setAttribute('aria-label', 'Remove file');
        del.appendChild(iconEl('close'));
        del.addEventListener('click', () => removeFile(f.name, f.size));
        row.appendChild(icon);
        row.appendChild(info);
        row.appendChild(del);
        list.appendChild(row);
    });
    document.getElementById('file-list-total').textContent =
        `${selectedFiles.length} • ${fmtSize(total)}`;
}

// ==================== SETTINGS ====================
function updateSettingUI() {
    document.getElementById('pad-val').textContent = document.getElementById('set-padding').value + ' ms';
    document.getElementById('freq-val').textContent = document.getElementById('set-freq').value + ' Hz';
    document.getElementById('gain-val').textContent = document.getElementById('set-gain').value + ' dB';
    saveSettingsLocally();
}
function saveSettingsLocally() {
    localStorage.setItem('app_settings', JSON.stringify({
        padding: document.getElementById('set-padding').value,
        freq: document.getElementById('set-freq').value,
        gain: document.getElementById('set-gain').value,
        format: document.getElementById('set-format').value,
        language: document.getElementById('set-language').value,
        model_size: document.getElementById('set-model-size').value,
        stem: document.getElementById('set-stem').checked,
        mute: document.getElementById('set-mute').checked,
        mode: document.querySelector('input[name="mode"]:checked').value
    }));
}
function loadSettings() {
    const s = JSON.parse(localStorage.getItem('app_settings') || '{}');
    if (s.padding) document.getElementById('set-padding').value = s.padding;
    if (s.freq) document.getElementById('set-freq').value = s.freq;
    if (s.gain) document.getElementById('set-gain').value = s.gain;
    if (s.format) document.getElementById('set-format').value = s.format;
    if (s.language) document.getElementById('set-language').value = s.language;
    if (s.model_size) document.getElementById('set-model-size').value = s.model_size;
    if (s.stem) document.getElementById('set-stem').checked = true;
    if (s.mute) document.getElementById('set-mute').checked = true;
    if (s.mode) { const el = document.querySelector(`input[name="mode"][value="${s.mode}"]`); if (el) el.checked = true; }
    updateSettingUI();
}
function onModeChange() { saveSettingsLocally(); }

// Превью бипа через Web Audio API
let audioCtx = null;
function previewBeep() {
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const freq = parseInt(document.getElementById('set-freq').value) || 1000;
        const gainDb = parseInt(document.getElementById('set-gain').value) || -10;
        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.value = freq;
        gainNode.gain.value = Math.pow(10, gainDb / 20);
        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.35);
    } catch (e) {
        showToast('Audio preview unavailable', 'error');
    }
}

// ==================== PRESETS ====================
function getPresets() { return JSON.parse(localStorage.getItem('filter_presets') || '{}'); }
function saveCurrentPreset() {
    const name = document.getElementById('new-preset-name').value.trim() || `Preset ${Object.keys(getPresets()).length + 1}`;
    if (!tags.length) return showToast(t('toast.noWords'), 'error');
    // Пресет теперь хранит и слова, и полные настройки обработки
    const settings = {
        mode: document.querySelector('input[name="mode"]:checked').value,
        padding: document.getElementById('set-padding').value,
        freq: document.getElementById('set-freq').value,
        gain: document.getElementById('set-gain').value,
        format: document.getElementById('set-format').value,
        language: document.getElementById('set-language').value,
        model_size: document.getElementById('set-model-size').value,
        stem: document.getElementById('set-stem').checked,
        mute: document.getElementById('set-mute').checked,
    };
    const p = getPresets();
    p[name] = { words: tags, settings };
    localStorage.setItem('filter_presets', JSON.stringify(p));
    document.getElementById('new-preset-name').value = '';
    renderPresets();
    showToast(t('tags.savePreset') + ': ' + name, 'success');
}
function deletePreset(name) {
    const p = getPresets(); delete p[name];
    localStorage.setItem('filter_presets', JSON.stringify(p)); renderPresets();
}
function renderPresets() {
    const p = getPresets();
    const list = document.getElementById('presets-list');
    const quick = document.getElementById('quick-presets-home');
    list.innerHTML = ''; quick.innerHTML = '';
    Object.keys(p).forEach(name => {
        const entry = p[name];
        const words = Array.isArray(entry) ? entry : (entry.words || []);
        const row = document.createElement('div');
        row.className = 'list-row';
        const info = document.createElement('div');
        info.className = 'list-row__body row';
        info.appendChild(iconEl('tag', 'list-row__icon'));
        const nameSpan = document.createElement('span');
        nameSpan.className = 'list-row__title';
        nameSpan.textContent = name;
        const countSpan = document.createElement('span');
        countSpan.className = 'badge';
        countSpan.textContent = words.length;
        info.appendChild(nameSpan);
        info.appendChild(countSpan);
        info.addEventListener('click', () => applyPreset(entry));
        const delBtn = document.createElement('button');
        delBtn.className = 'icon-btn';
        delBtn.setAttribute('aria-label', 'Delete preset');
        delBtn.appendChild(iconEl('trash'));
        delBtn.addEventListener('click', () => deletePreset(name));
        row.appendChild(info);
        row.appendChild(delBtn);
        list.appendChild(row);
        const bubble = document.createElement('button');
        bubble.className = 'pill';
        bubble.textContent = name;
        bubble.addEventListener('click', () => applyPreset(entry));
        quick.appendChild(bubble);
    });
}

function applyPreset(entry) {
    // Применяет пресет: слова + настройки (старые пресеты - только массив слов)
    if (Array.isArray(entry)) { setTags(entry); return; }
    setTags(entry.words || []);
    const s = entry.settings;
    if (!s) return;
    if (s.mode) { const el = document.querySelector(`input[name="mode"][value="${s.mode}"]`); if (el) el.checked = true; }
    if (s.padding != null) document.getElementById('set-padding').value = s.padding;
    if (s.freq != null) document.getElementById('set-freq').value = s.freq;
    if (s.gain != null) document.getElementById('set-gain').value = s.gain;
    if (s.format) document.getElementById('set-format').value = s.format;
    if (s.language) document.getElementById('set-language').value = s.language;
    if (s.model_size) document.getElementById('set-model-size').value = s.model_size;
    document.getElementById('set-stem').checked = !!s.stem;
    document.getElementById('set-mute').checked = !!s.mute;
    updateSettingUI();
}

// ==================== PROCESSING ====================
let currentTaskId = null;
let pollTimer = null;

function setStage(n) {
    // n = номер активной стадии (1..5), 0 = сброс, -1 = ошибка/отмена
    const ids = ['stage-upload', 'stage-transcribe', 'stage-analyze', 'stage-render', 'stage-concat'];
    ids.forEach((id, i) => {
        const el = document.getElementById(id);
        el.classList.remove('done', 'active', 'error');
        if (n === -1) { if (i === 0) el.classList.add('error'); return; }
        if (i + 1 < n) el.classList.add('done');
        else if (i + 1 === n) el.classList.add('active');
    });
}

function mapStatusToStage(status) {
    if (/транскриб|transcrib/i.test(status)) return 2;
    if (/анализ|analy|файл \d/i.test(status)) return 3;
    if (/рендер|render|обработк|нарезк|сборк|audio/i.test(status)) return 4;
    if (/склейк|concat|merge/i.test(status)) return 5;
    return 0;
}

function resetProgressUI() {
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('percent-text').textContent = '0%';
    document.getElementById('status-text').textContent = t('stage.upload') + '...';
    setStage(0);
}

async function startProcessing() {
    const urlValue = document.getElementById('url-input').value.trim();
    if (!selectedFiles.length && !urlValue) return showToast(t('toast.noFile'), 'error');
    const mode = document.querySelector('input[name="mode"]:checked').value;
    if (mode !== 'summarize' && !tags.length) return showToast(t('toast.noWords'), 'error');

    document.getElementById('start-btn').classList.add('hidden');
    document.getElementById('progress-area').classList.remove('hidden');
    resetProgressUI();

    const fd = new FormData();
    selectedFiles.forEach(f => fd.append('file', f));
    fd.append('words', tags.join(','));
    fd.append('mode', mode);
    fd.append('padding', document.getElementById('set-padding').value);
    fd.append('format', document.getElementById('set-format').value);
    fd.append('beep_freq', document.getElementById('set-freq').value);
    fd.append('beep_gain', document.getElementById('set-gain').value);
    fd.append('mute', document.getElementById('set-mute').checked ? '1' : '0');
    fd.append('stem_match', document.getElementById('set-stem').checked ? '1' : '0');
    fd.append('language', document.getElementById('set-language').value);
    fd.append('model_size', document.getElementById('set-model-size').value);
    fd.append('url', document.getElementById('url-input').value.trim());

    // XHR для отслеживания прогресса загрузки файлов
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/process');
    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 10); // загрузка = 0..10%
            document.getElementById('status-text').textContent = t('stage.upload') + ` ${Math.round(e.loaded / e.total * 100)}%`;
            document.getElementById('percent-text').textContent = pct + '%';
            document.getElementById('progress-bar').style.width = pct + '%';
        }
    };
    xhr.onload = () => {
        let d = {};
        try { d = JSON.parse(xhr.responseText); } catch (e) { }
        if (xhr.status !== 200 || d.error) {
            showToast(d.error || t('toast.connError'), 'error');
            restoreStartUI();
            return;
        }
        currentTaskId = d.task_id;
        showToast(t('toast.uploadDone'), 'success');
        pollStatus(d.task_id);
    };
    xhr.onerror = () => { showToast(t('toast.connError'), 'error'); restoreStartUI(); };
    xhr.send(fd);
}

function restoreStartUI() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    document.getElementById('start-btn').classList.remove('hidden');
    document.getElementById('progress-area').classList.add('hidden');
    currentTaskId = null;
}

async function cancelCurrentJob() {
    if (!currentTaskId) return;
    try {
        await fetch(`/cancel/${currentTaskId}`, { method: 'POST' });
        showToast(t('toast.cancelled'), 'info');
    } catch (e) { }
}

function pollStatus(taskId) {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
        try {
            const rs = await fetch(`/status/${taskId}`);
            const ds = await rs.json();
            if (ds.status === 'unknown') { clearInterval(pollTimer); return; }

            document.getElementById('status-text').textContent =
                ds.status_key ? t(ds.status_key, ds.status_vars) : ds.status;
            document.getElementById('percent-text').textContent = ds.percent + '%';
            document.getElementById('progress-bar').style.width = ds.percent + '%';
            const st = mapStatusToStage(ds.status);
            if (st) setStage(st);

            if (ds.status === 'completed' || ds.status === 'error' || ds.status === 'cancelled') {
                clearInterval(pollTimer);
                pollTimer = null;
                restoreStartUI();
                if (ds.status === 'completed') {
                    fillResults(ds);
                    switchTab('results');
                    // Бейдж не показываем: мы уже на вкладке Results
                } else {
                    setStage(-1);
                    showToast(ds.error || ds.status, 'error');
                }
                currentTaskId = null;
            }
        } catch (e) {
            clearInterval(pollTimer);
            pollTimer = null;
            restoreStartUI();
            showToast(t('toast.connError'), 'error');
        }
    }, 1000);
}

// ==================== RESULTS ====================
function fmtTime(seconds) {
    const s = Math.max(0, Math.floor(seconds));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

function seekTo(t) {
    // Перемотка в плеере (волновая форма или нативный аудио/видео)
    if (wavesurfer) { wavesurfer.setTime(t); wavesurfer.play(); return; }
    const el = document.getElementById('media-preview-container').querySelector('video, audio');
    if (el) { el.currentTime = t; el.play(); }
}

function escapeRegExp(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

// Нормализация слова так же, как на сервере (убираем пунктуацию и регистр),
// иначе подсветка в транскрипте не срабатывает («мат,» != «мат»).
function normWord(s) { return (s || '').toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, '').trim(); }

function appendHighlighted(container, text, words) {
    const normWords = words.map(normWord).filter(Boolean);
    const normSet = new Set(normWords);
    // Безопасная подсветка найденных слов в тексте (без innerHTML)
    if (!words.length) { container.appendChild(document.createTextNode(text + ' ')); return; }
    const re = new RegExp('(' + normWords.map(escapeRegExp).join('|') + ')', 'gi');
    text.split(re).forEach(p => {
        if (!p) return;
        if (normSet.has(normWord(p))) {
            const mark = document.createElement('span');
            mark.className = 'hl-word';
            mark.textContent = p;
            container.appendChild(mark);
        } else {
            container.appendChild(document.createTextNode(p));
        }
    });
    container.appendChild(document.createTextNode(' '));
}

let transcriptSegments = [];
let currentSummary = '';
let currentMatchWords = [];
let wavesurfer = null;

function fillResults(data) {
    document.getElementById('result-status-card').classList.add('hidden');
    document.getElementById('results-content').classList.remove('hidden');

    const filename = data.filename || '';
    document.getElementById('btn-download-media').href = data.download_url;
    document.getElementById('dl-text').textContent = `${t('history.download')} (${filename})`;

    const btnSrt = document.getElementById('btn-download-srt');
    const btnTxt = document.getElementById('btn-download-txt');
    if (data.srt_url) btnSrt.href = data.srt_url;
    if (data.txt_url) btnTxt.href = data.txt_url;
    const btnHl = document.getElementById('btn-download-hl');
    const btnJson = document.getElementById('btn-download-json');
    if (data.highlight_srt_url) btnHl.href = data.highlight_srt_url;
    if (data.report_url) btnJson.href = data.report_url;

    const container = document.getElementById('media-preview-container');
    const playerWrapper = container.parentElement;

    const isTextOutput = filename.toLowerCase().endsWith('.txt');
    const isVideo = data.is_video && !isTextOutput;

    container.innerHTML = '';

    // Показываем вкладку "AI Summary" только если есть сводка
    currentSummary = data.summary_text || '';
    currentMatchWords = [...new Set((data.matches_list || []).map(m => normWord(m.word)).filter(Boolean))].sort((a, b) => b.length - a.length);
    const summaryTab = document.getElementById('res-tab-summarize');
    if (currentSummary) summaryTab.classList.remove('hidden');
    else summaryTab.classList.add('hidden');

    if (isTextOutput) {
        playerWrapper.classList.add('hidden');
        toggleResultView('summarize');
    } else {
        playerWrapper.classList.remove('hidden');
        if (wavesurfer) { try { wavesurfer.destroy(); } catch (e) { } wavesurfer = null; }
        const mediaName = (data.download_url || '').split('/').pop();
        const mediaUrl = mediaName ? '/media/' + mediaName : data.download_url;
        // Волновая форма с маркерами совпадений (wavesurfer, если доступен и есть совпадения)
        if (!isVideo && currentMatchWords.length && window.WaveSurfer) {
            try {
                wavesurfer = WaveSurfer.create({
                    container,
                    waveColor: '#3b82f6',
                    progressColor: '#60a5fa',
                    cursorColor: '#ef4444',
                    height: 90,
                    barWidth: 2,
                    url: mediaUrl,
                });
                (data.matches_list || []).forEach(m => {
                    wavesurfer.addRegion({ start: m.start, end: m.end + 0.05, color: 'rgba(239,68,68,0.25)', drag: false });
                });
                wavesurfer.on('region-click', (region) => { wavesurfer.setTime(region.start); wavesurfer.play(); });
            } catch (e) {
                wavesurfer = null;
            }
        }
        if (!wavesurfer) {
            const media = isVideo ? document.createElement('video') : document.createElement('audio');
            media.controls = true;
            media.className = '';
            media.src = mediaUrl;
            container.appendChild(media);
        }
        toggleResultView('table');
    }

    // --- ТАБЛИЦА СОВПАДЕНИЙ (Matches) ---
    const tbody = document.getElementById('matches-table-body');
    tbody.innerHTML = '';
    if (data.matches_list && data.matches_list.length) {
        data.matches_list.forEach(m => {
            const tr = document.createElement('tr');
            tr.className = 'is-clickable';
            if (!isTextOutput) {
                tr.addEventListener('click', () => { seekTo(m.start); });
            }
            const tdTime = document.createElement('td');
            tdTime.className = 'table__time';
            tdTime.textContent = fmtTime(m.start);
            const tdWord = document.createElement('td');
            tdWord.className = 'table__word';
            tdWord.textContent = m.word;
            const tdCtx = document.createElement('td');
            tdCtx.className = 'table__context';
            tdCtx.textContent = m.context || '';
            tr.appendChild(tdTime);
            tr.appendChild(tdWord);
            tr.appendChild(tdCtx);
            tbody.appendChild(tr);
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="3" class="table__empty">—</td></tr>';
    }

    // --- СТАТИСТИКА (word_counts) ---
    const sbody = document.getElementById('summary-table-body');
    sbody.innerHTML = '';
    if (data.word_counts && Object.keys(data.word_counts).length) {
        const sorted = Object.entries(data.word_counts).sort((a, b) => b[1] - a[1]);
        sorted.forEach(([word, count]) => {
            const tr = document.createElement('tr');
            const tdWord = document.createElement('td');
            tdWord.className = 'table__word';
            tdWord.textContent = word;
            const tdCount = document.createElement('td');
            tdCount.className = 'table__time';
            tdCount.textContent = count;
            tr.appendChild(tdWord);
            tr.appendChild(tdCount);
            sbody.appendChild(tr);
        });
    } else {
        sbody.innerHTML = '<tr><td colspan="2" class="table__empty">—</td></tr>';
    }

    // --- ПОЛНЫЙ ТЕКСТ (с поиском) ---
    transcriptSegments = data.full_transcript || [];
    document.getElementById('transcript-search').value = '';
    renderTranscript('');

    // --- ПЕРЕСКАЗ ---
    const summaryContainer = document.getElementById('summarize-text');
    summaryContainer.innerHTML = '';
    if (currentSummary) {
        const p = document.createElement('p');
        p.className = 'summary-text';
        p.textContent = currentSummary;
        summaryContainer.appendChild(p);
    } else {
        summaryContainer.innerHTML = '<div class="empty-state">' + iconHtml('ghost') + '<p>' + t('results.empty') + '</p></div>';
    }
}

function renderTranscript(query) {
    const txtContainer = document.getElementById('transcript-text');
    txtContainer.innerHTML = '';
    const q = query.trim().toLowerCase();
    let shown = 0;
    transcriptSegments.forEach(seg => {
        if (q && !seg.text.toLowerCase().includes(q)) return;
        shown++;
        const span = document.createElement('span');
        span.className = 'seg';
        appendHighlighted(span, seg.text, currentMatchWords);
        span.addEventListener('click', () => seekTo(seg.start));
        txtContainer.appendChild(span);
    });
    const hasMedia = !!document.getElementById('media-preview-container').querySelector('video, audio') || !!wavesurfer;
    if (!hasMedia) txtContainer.querySelectorAll('span').forEach(s => s.classList.add('is-quiet'));
    document.getElementById('transcript-count').textContent = q ? `${shown}/${transcriptSegments.length}` : '';
}

function filterTranscript() {
    renderTranscript(document.getElementById('transcript-search').value);
}

function copySummary() {
    if (!currentSummary) return;
    navigator.clipboard.writeText(currentSummary).then(() => showToast(t('toast.copied'), 'success'));
}

// ==================== HISTORY ====================
async function loadHistory() {
    const list = document.getElementById('history-list');
    try {
        const r = await fetch('/history');
        const items = await r.json();
        list.innerHTML = '';
        if (!items.length) {
            list.innerHTML = `<p class="empty-state">${t('history.empty')}</p>`;
            return;
        }
        items.forEach(item => {
            const row = document.createElement('div');
            row.className = 'list-row';
            const icon = iconEl(item.status === 'completed' ? 'check-circle' : 'x-circle',
                'list-row__icon ' + (item.status === 'completed' ? 'list-row__icon--ok' : 'list-row__icon--bad'));
            const info = document.createElement('div');
            info.className = 'list-row__body';
            const name = document.createElement('p');
            name.className = 'list-row__title';
            name.textContent = (item.filenames && item.filenames[0]) || item.filename || item.task_id;
            if (item.filenames && item.filenames.length > 1) name.textContent += ` (+${item.filenames.length - 1})`;
            const meta = document.createElement('p');
            meta.className = 'list-row__meta';
            const date = item.finished_at ? new Date(item.finished_at * 1000).toLocaleString() : '';
            const matchesLabel = t('history.matches', { n: item.match_count || 0 });
            meta.textContent = `${item.mode || ''} • ${date} • ${matchesLabel}`;
            info.appendChild(name);
            info.appendChild(meta);
            row.appendChild(icon);
            row.appendChild(info);
            if (item.status === 'completed') {
                const openBtn = document.createElement('button');
                openBtn.className = 'btn btn--primary btn--sm list-row__action';
                openBtn.textContent = t('history.open');
                openBtn.addEventListener('click', async () => {
                    try {
                        const r2 = await fetch(`/results/${item.task_id}`);
                        const d2 = await r2.json();
                        if (!d2.error) { fillResults(d2); window.scrollTo({ top: 0, behavior: 'smooth' }); }
                    } catch (e) { }
                });
                row.appendChild(openBtn);
                if (item.download_url) {
                    const dl = document.createElement('a');
                    dl.className = 'btn btn--ghost btn--icon list-row__action';
                    dl.href = item.download_url;
                    dl.appendChild(iconEl('download'));
                    dl.setAttribute('aria-label', t('history.download'));
                    row.appendChild(dl);
                }
            } else {
                const err = document.createElement('span');
                err.className = 'badge badge--bad list-row__action';
                err.textContent = item.error || item.status;
                row.appendChild(err);
            }
            list.appendChild(row);
        });
    } catch (e) {
        list.innerHTML = `<p class="empty-state">${t('toast.connError')}</p>`;
    }
}

// Восстанавливаем последние слова и проверяем готовность окружения
try {
    const savedTags = JSON.parse(localStorage.getItem('app_tags') || '[]');
    if (Array.isArray(savedTags)) { tags = savedTags; renderTags(); }
} catch (e) { }
checkHealth();

async function checkHealth() {
    // Мягкая проверка окружения: пользователь сразу видит, чего не хватает
    try {
        const r = await fetch('/health');
        const h = await r.json();
        if (!h.ffmpeg) showToast(t('toast.ffmpegMissing'), 'error');
        if (!h.ollama) showToast(t('toast.ollamaOffline'), 'info');
        else if (!h.llm_model_ready) showToast(t('toast.modelNotLoaded', { model: h.llm_model }), 'info');
    } catch (e) { }
}
// ==================== INIT ====================
loadSettings();
renderPresets();
applyLang();
