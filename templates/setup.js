// ==================== SETUP WIZARD (модели, FFmpeg, Ollama) ====================
// Отдельный файл: логика первичной настройки и скачивания моделей.
// Загружается после script.js и переиспользует I18N/applyLang/showToast.
Object.assign(I18N.ru, {
    'setup.title': 'Первичная настройка',
    'setup.subtitle': 'Проверим окружение и скачаем модели - конфиги трогать не нужно.',
    'setup.check': 'Проверить снова', 'setup.done': 'Готово',
    'setup.ffmpeg': 'FFmpeg (обработка медиа)', 'setup.whisper': 'Модель распознавания речи',
    'setup.ollama': 'Ollama (сводки)', 'setup.download': 'Скачать модель',
    'setup.startOllama': 'Запустить Ollama', 'setup.pullLlm': 'Скачать LLM',
    'setup.system': 'Система', 'setup.open': 'Мастер настройки', 'setup.copyReport': 'Скопировать отчёт',
    'setup.loading': 'Проверяю окружение...',
    'setup.ok': 'готово', 'setup.missing': 'не найдено', 'setup.offline': 'не запущена',
    'setup.ready': 'Всё готово к работе', 'setup.needs': 'Требуется внимание',
    'setup.whisperHint': 'Устройство: {device}, ОЗУ: {mem} ГБ. Рекомендуемый размер: {rec}.',
    'setup.downloaded': 'Скачано', 'setup.ollamaModels': 'Модели', 'setup.llmModel': 'LLM-модель',
    'setup.recommended': 'рекомендуется',
    'setup.downloadStarted': 'Скачивание модели началось', 'setup.pullStarted': 'Загрузка модели Ollama началась',
    'setup.ollamaRunning': 'Ollama уже запущена', 'setup.ollamaStarted': 'Ollama запущена',
    'setup.downloadFfmpeg': 'Скачать FFmpeg',
    'setup.ffmpegStarted': 'Скачивание FFmpeg началось - прогресс в этом окне',
    'setup.ffmpegHint': 'FFmpeg скачается один раз в каталог данных и больше не потребует настроек.',
    'setup.finished': 'готово', 'setup.error': 'ошибка'
});
Object.assign(I18N.en, {
    'setup.title': 'First-run setup',
    'setup.subtitle': 'We will check the environment and download models - no manual config needed.',
    'setup.check': 'Check again', 'setup.done': 'Done',
    'setup.ffmpeg': 'FFmpeg (media processing)', 'setup.whisper': 'Speech recognition model',
    'setup.ollama': 'Ollama (summaries)', 'setup.download': 'Download model',
    'setup.startOllama': 'Start Ollama', 'setup.pullLlm': 'Download LLM',
    'setup.system': 'System', 'setup.open': 'Setup wizard', 'setup.copyReport': 'Copy report',
    'setup.loading': 'Checking environment...',
    'setup.ok': 'ready', 'setup.missing': 'missing', 'setup.offline': 'not running',
    'setup.ready': 'Everything is ready', 'setup.needs': 'Needs attention',
    'setup.whisperHint': 'Device: {device}, RAM: {mem} GB. Recommended size: {rec}.',
    'setup.downloaded': 'Downloaded', 'setup.ollamaModels': 'Models', 'setup.llmModel': 'LLM model',
    'setup.recommended': 'recommended',
    'setup.downloadStarted': 'Model download started', 'setup.pullStarted': 'Ollama model pull started',
    'setup.ollamaRunning': 'Ollama is already running', 'setup.ollamaStarted': 'Ollama started',
    'setup.downloadFfmpeg': 'Download FFmpeg',
    'setup.ffmpegStarted': 'FFmpeg download started - progress is shown here',
    'setup.ffmpegHint': 'FFmpeg is downloaded once into the data folder - no manual setup required.',
    'setup.finished': 'done', 'setup.error': 'error'
});

let setupState = null;
let setupTasks = {};
let setupPollTimer = null;

async function setupFetch(url, options) {
    const response = await fetch(url, options);
    let data = {};
    try { data = await response.json(); } catch (e) { data = {}; }
    if (!response.ok) {
        const detail = data.error || ('HTTP ' + response.status);
        throw new Error(data.hint ? detail + ' - ' + data.hint : detail);
    }
    return data;
}

function setupBadge(id, kind, text) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    const variants = { ok: 'badge badge--ok', warn: 'badge badge--warn', bad: 'badge badge--bad' };
    el.className = variants[kind] || variants.warn;
}

function renderSetup() {
    if (!setupState) return;
    const state = setupState;
    const whisperReady = state.whisper.default_ready || (state.whisper.local_sizes || []).length > 0;

    setupBadge('setup-ffmpeg-badge', state.ffmpeg.ok ? 'ok' : 'bad',
        state.ffmpeg.ok ? t('setup.ok') : t('setup.missing'));
    const ffmpegHint = document.getElementById('setup-ffmpeg-hint');
    if (ffmpegHint) {
        ffmpegHint.textContent = state.ffmpeg.ok
            ? (state.ffmpeg.version || state.ffmpeg.path)
            : [state.ffmpeg.hint, t('setup.ffmpegHint')].filter(Boolean).join(' ');
        ffmpegHint.classList.toggle('hidden', !ffmpegHint.textContent);
    }
    const ffmpegButton = document.getElementById('setup-ffmpeg-download');
    if (ffmpegButton) {
        const build = state.ffmpeg.download || {};
        const running = !!(state.ffmpeg.task && state.ffmpeg.task.status === 'running');
        ffmpegButton.classList.toggle('hidden', !!state.ffmpeg.ok || !build.supported);
        ffmpegButton.disabled = running;
        ffmpegButton.title = build.supported
            ? (build.size_mb ? '~' + build.size_mb + ' MB -> ' + (build.install_dir || '') : (build.install_dir || ''))
            : (build.hint || '');
    }

    setupBadge('setup-whisper-badge', whisperReady ? 'ok' : 'warn',
        whisperReady ? t('setup.ok') : t('setup.missing'));
    const whisperHint = document.getElementById('setup-whisper-hint');
    if (whisperHint) {
        whisperHint.textContent = t('setup.whisperHint')
            .replace('{device}', state.device)
            .replace('{mem}', state.memory_gb)
            .replace('{rec}', state.recommended_size)
            + ((state.whisper.local_sizes || []).length
                ? '. ' + t('setup.downloaded') + ': ' + state.whisper.local_sizes.join(', ') : '');
    }

    const select = document.getElementById('setup-model-size');
    if (select && !select.dataset.filled) {
        select.innerHTML = '';
        (state.whisper.catalog || []).forEach(item => {
            const option = document.createElement('option');
            option.value = item.size;
            const marks = (item.recommended ? ' ★' : '') + (item.present ? ' ✓' : '');
            option.textContent = item.size + ' · ~' + item.size_mb + ' MB' + marks;
            if (item.recommended) option.selected = true;
            select.appendChild(option);
        });
        select.dataset.filled = '1';
    }

    const ollama = state.ollama;
    setupBadge('setup-ollama-badge', ollama.running ? (ollama.model_ready ? 'ok' : 'warn') : 'bad',
        ollama.running ? (ollama.model_ready ? t('setup.ok') : t('setup.missing')) : t('setup.offline'));
    const ollamaHint = document.getElementById('setup-ollama-hint');
    if (ollamaHint) {
        ollamaHint.textContent = ollama.running
            ? t('setup.ollamaModels') + ': ' + ((ollama.models || []).join(', ') || '—') + ' · ' + ollama.url
            : (ollama.hint || ollama.url);
    }
    const modelInput = document.getElementById('setup-ollama-model');
    if (modelInput && !modelInput.value) modelInput.value = ollama.model || '';
    if (typeof populateModelOptions === 'function') {
        populateModelOptions(ollama.models || [], ollama.catalog || []);
    }

    const summary = document.getElementById('setup-summary');
    if (summary) {
        summary.textContent = state.ready ? t('setup.ready') : t('setup.needs');
        summary.className = 'badge ' + (state.ready ? 'badge--ok' : 'badge--warn');
    }

    renderSetupTasks();
    renderSystemCard();
}

function renderSetupTasks() {
    const wrap = document.getElementById('setup-progress-wrap');
    const bar = document.getElementById('setup-progress-bar');
    const label = document.getElementById('setup-progress-text');
    if (!wrap) return;
    const keys = Object.keys(setupTasks || {})
        .sort((a, b) => (setupTasks[b].updated_at || 0) - (setupTasks[a].updated_at || 0));
    const task = keys.length ? setupTasks[keys[0]] : null;
    if (typeof renderModelsProgress === 'function') renderModelsProgress(setupTasks);
    if (!task) { wrap.classList.add('hidden'); return; }
    wrap.classList.remove('hidden');
    const percent = task.status === 'done' ? 100 : (task.progress || 0);
    if (bar) bar.style.width = percent + '%';
    if (label) {
        const name = task.label || '';
        if (task.status === 'error') label.textContent = name + ': ' + (task.error || t('setup.error'));
        else if (task.status === 'done') label.textContent = name + ': ' + t('setup.finished');
        else label.textContent = name + ': ' + (task.status_text || '') + ' ' + percent + '%'
            + (task.downloaded_mb ? ' (' + task.downloaded_mb + ' MB)' : '');
    }
}

function startSetupPolling() {
    if (setupPollTimer) return;
    setupPollTimer = setInterval(async () => {
        try {
            setupTasks = await setupFetch('/api/models/tasks');
        } catch (e) {
            return;
        }
        renderSetupTasks();
        const running = Object.keys(setupTasks).some(key => setupTasks[key].status === 'running');
        if (!running) {
            clearInterval(setupPollTimer);
            setupPollTimer = null;
            refreshSetup();
        }
    }, 1500);
}

async function refreshSetup() {
    try {
        setupState = await setupFetch('/api/setup');
    } catch (e) {
        showToast(t('toast.connError'), 'error');
        return null;
    }
    renderSetup();
    return setupState;
}

async function downloadWhisperModel() {
    const select = document.getElementById('setup-model-size');
    const size = select ? select.value : '';
    if (!size) return;
    const button = document.getElementById('setup-download-btn');
    if (button) button.disabled = true;
    try {
        await setupFetch('/api/models/whisper/download', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ size: size })
        });
        showToast(t('setup.downloadStarted'), 'info');
        startSetupPolling();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (button) button.disabled = false;
    }
}

async function downloadFfmpeg() {
    // Бинарники качаются в каталог данных: дистрибутив остаётся маленьким.
    const button = document.getElementById('setup-ffmpeg-download');
    if (button) button.disabled = true;
    try {
        await setupFetch('/api/binaries/ffmpeg/download', { method: 'POST' });
        showToast(t('setup.ffmpegStarted'), 'info');
        startSetupPolling();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (button) button.disabled = false;
    }
}

async function pullLlmModel() {
    // Модель берём из поля ввода мастера: можно скачать любую из библиотеки Ollama.
    const input = document.getElementById('setup-ollama-model');
    const typed = input ? input.value.trim() : '';
    const fallback = (setupState && setupState.ollama && setupState.ollama.model) || '';
    const model = typed || fallback;
    if (!model) { showToast(t('models.needName'), 'error'); return; }
    const button = document.getElementById('setup-ollama-pull');
    if (button) button.disabled = true;
    try {
        await setupFetch('/api/models/ollama/pull', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: model, activate: true })
        });
        showToast(t('models.pullStarted').replace('{m}', model), 'info');
        startSetupPolling();
        if (typeof startModelsPolling === 'function') startModelsPolling();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (button) button.disabled = false;
    }
}

async function startOllamaFromSetup() {
    try {
        const data = await setupFetch('/api/ollama/start', { method: 'POST' });
        showToast(data.already_running ? t('setup.ollamaRunning') : t('setup.ollamaStarted'), 'success');
    } catch (e) {
        showToast(e.message, 'error');
    }
    refreshSetup();
}

function openSetupWizard() {
    const modal = document.getElementById('setup-modal');
    if (!modal) return;
    modal.classList.add('is-open');
    refreshSetup();
    startSetupPolling();
}

function closeSetupWizard() {
    const modal = document.getElementById('setup-modal');
    if (modal) modal.classList.remove('is-open');
    localStorage.setItem('setup_wizard_done', '1');
}

// Клик по затемнению закрывает мастер
document.addEventListener('click', event => {
    const modal = document.getElementById('setup-modal');
    if (modal && event.target === modal) closeSetupWizard();
});
document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeSetupWizard();
});

function renderSystemCard() {
    const box = document.getElementById('system-status-text');
    if (!box || !setupState) return;
    const state = setupState;
    const rows = [
        [state.ffmpeg.ok, t('setup.ffmpeg')],
        [state.whisper.default_ready || (state.whisper.local_sizes || []).length > 0,
            t('setup.whisper') + ' (' + ((state.whisper.local_sizes || []).join(', ') || state.whisper.default_size) + ')'],
        [state.ollama.running,
            t('setup.ollama') + ' (' + (state.ollama.running ? 'OK' : t('setup.offline')) + ')'],
        [state.ollama.model_ready, t('setup.llmModel') + ' (' + state.ollama.model + ')']
    ];
    box.innerHTML = '';
    rows.forEach(row => {
        const line = document.createElement('p');
        line.className = 'status-line ' + (row[0] ? 'status-line--ok' : 'status-line--warn');
        line.appendChild(iconEl(row[0] ? 'check-circle' : 'warning'));
        const text = document.createElement('span');
        text.textContent = row[1];
        line.appendChild(text);
        box.appendChild(line);
    });
    const info = document.createElement('p');
    info.className = 'list-row__meta';
    info.textContent = state.device + '/' + state.compute_type + ' · RAM ' + state.memory_gb + ' GB · '
        + t('setup.recommended') + ': ' + state.recommended_size;
    box.appendChild(info);
}

async function refreshSystemCard() {
    await refreshSetup();
}

async function copySystemReport() {
    if (!setupState) await refreshSetup();
    if (!setupState) return;
    let health = {};
    try { health = await setupFetch('/health'); } catch (e) { health = {}; }
    const report = [
        'Cutline system report',
        'OS: ' + setupState.platform.os + ' ' + setupState.platform.release,
        'Python: ' + setupState.platform.python + ' (frozen: ' + setupState.platform.frozen + ')',
        'Device: ' + setupState.device + '/' + setupState.compute_type,
        'RAM: ' + setupState.memory_gb + ' GB, disk free: ' + setupState.disk_free_gb + ' GB',
        'FFmpeg: ' + (setupState.ffmpeg.ok ? setupState.ffmpeg.path : 'MISSING'),
        'Whisper: ' + ((setupState.whisper.local_sizes || []).join(', ') || 'none'),
        'Ollama: ' + (setupState.ollama.running ? 'running' : 'offline') + ' (' + setupState.ollama.url + ')',
        'Ollama models: ' + ((setupState.ollama.models || []).join(', ') || 'none'),
        'Warnings: ' + ((setupState.warnings || []).join('; ') || 'none'),
        'Health: ' + JSON.stringify(health)
    ].join('\n');
    try {
        await navigator.clipboard.writeText(report);
        showToast(t('toast.copied'), 'success');
    } catch (e) {
        showToast(t('toast.connError'), 'error');
    }
}

// Перерисовка новых ключей i18n и авто-показ мастера при первом запуске.
applyLang();
(async function autoOpenSetupWizard() {
    const state = await refreshSetup();
    if (!state) return;
    if (!localStorage.getItem('setup_wizard_done')) openSetupWizard();
})();
