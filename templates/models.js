// ==================== МОДЕЛИ: СПИСОК, ВЫБОР, СКАЧИВАНИЕ ====================
// Загружается после script.js/setup.js: использует I18N, t(), showToast, setupFetch.
// Здесь живёт вся логика карточки «Модели ИИ» в настройках:
//   - список уже скачанных моделей Ollama и выбор активной (без конфигов),
//   - скачивание любой модели по имени,
//   - импорт GGUF по прямой ссылке,
//   - скачивание модели распознавания речи.
Object.assign(I18N.ru, {
    'models.title': 'Модели ИИ',
    'models.loading': 'Проверяю модели...',
    'models.installed': 'Уже установлены в Ollama',
    'models.pullByName': 'Скачать по имени',
    'models.namePh': 'например gemma3:4b',
    'models.download': 'Скачать',
    'models.pullHint': 'Любая модель из библиотеки Ollama: llama3.2, qwen2.5:7b, mistral…',
    'models.importTitle': 'Импорт по ссылке (.gguf)',
    'models.importNamePh': 'имя модели',
    'models.import': 'Импорт',
    'models.importHint': 'Прямая ссылка на GGUF-файл: скачаем и создадим модель через Ollama.',
    'models.whisperTitle': 'Модель распознавания речи',
    'models.whisperDownload': 'Скачать',
    'models.whisperPresent': 'Скачано: {list}',
    'models.offline': 'Ollama не запущена',
    'models.notReady': 'модель не выбрана',
    'models.noModels': 'Пока ничего не скачано - впишите имя модели ниже',
    'models.selectHint': 'Нажмите на модель, чтобы использовать её для пересказа.',
    'models.selected': 'Модель пересказа: {m}',
    'models.pullStarted': 'Скачивание «{m}» началось',
    'models.importStarted': 'Импорт «{m}» начался',
    'models.whisperStarted': 'Скачивание модели распознавания началось',
    'models.needName': 'Укажите имя модели',
    'models.needUrl': 'Укажите прямую ссылку на .gguf',
    'models.active': 'пересказ'
});
Object.assign(I18N.en, {
    'models.title': 'AI models',
    'models.loading': 'Checking models...',
    'models.installed': 'Already installed in Ollama',
    'models.pullByName': 'Download by name',
    'models.namePh': 'e.g. gemma3:4b',
    'models.download': 'Download',
    'models.pullHint': 'Any model from the Ollama library: llama3.2, qwen2.5:7b, mistral…',
    'models.importTitle': 'Import from link (.gguf)',
    'models.importNamePh': 'model name',
    'models.import': 'Import',
    'models.importHint': 'Direct link to a GGUF file: we download it and create the model via Ollama.',
    'models.whisperTitle': 'Speech recognition model',
    'models.whisperDownload': 'Download',
    'models.whisperPresent': 'Downloaded: {list}',
    'models.offline': 'Ollama is not running',
    'models.notReady': 'no model selected',
    'models.noModels': 'Nothing downloaded yet - type a model name below',
    'models.selectHint': 'Click a model to use it for summaries.',
    'models.selected': 'Summary model: {m}',
    'models.pullStarted': 'Download of "{m}" started',
    'models.importStarted': 'Import of "{m}" started',
    'models.whisperStarted': 'Speech model download started',
    'models.needName': 'Enter a model name',
    'models.needUrl': 'Enter a direct .gguf link',
    'models.active': 'summary'
});

let modelsState = null;
let modelsPollTimer = null;
let modelsRefreshTimer = null;

function modelsRequest(url, options) {
    return setupFetch(url, options);
}

// Краткая подсказка о модели из каталога (если она там есть)
function modelNote(name, catalog) {
    const short = name.split(':')[0];
    const found = (catalog || []).find(item => item.name === name || item.name.split(':')[0] === short);
    return found ? found.note : '';
}

function isActiveModel(name, active) {
    if (!name || !active) return false;
    return name === active || name.split(':')[0] === active.split(':')[0];
}

function populateModelOptions(models, catalog) {
    const names = [];
    (models || []).forEach(name => { if (name && !names.includes(name)) names.push(name); });
    (catalog || []).forEach(item => { if (item.name && !names.includes(item.name)) names.push(item.name); });
    ['models-datalist', 'models-datalist-fed'].forEach(id => {
        const list = document.getElementById(id);
        if (!list) return;
        list.innerHTML = '';
        names.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            list.appendChild(option);
        });
    });
}

function renderModels(state) {
    if (!state) return;
    modelsState = state;
    const ollama = state.ollama || {};
    const models = ollama.models || [];
    const catalog = ollama.catalog || [];
    const active = ollama.model || '';
    const ready = models.some(name => isActiveModel(name, active));

    const badge = document.getElementById('models-active-badge');
    if (badge) {
        badge.className = 'badge ' + (!ollama.running ? 'badge--bad' : ready ? 'badge--ok' : 'badge--warn');
        badge.textContent = !ollama.running ? t('models.offline') : (active || t('models.notReady'));
        badge.title = t('models.active') + ': ' + (active || '—');
    }

    const status = document.getElementById('models-status');
    if (status) {
        if (!ollama.running) status.textContent = ollama.hint || (ollama.url || '');
        else if (!models.length) status.textContent = t('models.noModels');
        else status.textContent = t('models.selectHint') + ' · ' + (ollama.url || '');
    }

    const count = document.getElementById('models-count');
    if (count) count.textContent = models.length ? String(models.length) : '';

    const list = document.getElementById('models-list');
    if (list) {
        list.innerHTML = '';
        if (!models.length) {
            const empty = document.createElement('p');
            empty.className = 'empty-state';
            empty.appendChild(iconEl('package'));
            const text = document.createElement('span');
            text.textContent = t('models.noModels');
            empty.appendChild(text);
            list.appendChild(empty);
        }
        models.slice().sort().forEach(name => {
            const row = document.createElement('button');
            row.type = 'button';
            const activeRow = isActiveModel(name, active);
            row.className = 'model-row' + (activeRow ? ' is-active' : '');
            row.setAttribute('aria-pressed', activeRow ? 'true' : 'false');

            const radio = document.createElement('span');
            radio.className = 'model-row__radio';
            radio.appendChild(iconEl('check'));
            row.appendChild(radio);

            const body = document.createElement('span');
            body.className = 'grow';
            const title = document.createElement('span');
            title.className = 'model-row__name';
            title.textContent = name;
            body.appendChild(title);
            const note = modelNote(name, catalog);
            if (note) {
                const hint = document.createElement('span');
                hint.className = 'model-row__note';
                hint.textContent = note;
                body.appendChild(hint);
            }
            row.appendChild(body);

            if (activeRow) {
                const badgeEl = document.createElement('span');
                badgeEl.className = 'badge badge--accent';
                badgeEl.textContent = t('models.active');
                row.appendChild(badgeEl);
            }
            row.addEventListener('click', () => selectModel(name));
            list.appendChild(row);
        });
    }

    const whisperSelect = document.getElementById('models-whisper-size');
    const whisper = state.whisper || {};
    if (whisperSelect) {
        const signature = JSON.stringify((whisper.catalog || []).map(item => item.size));
        if (whisperSelect.dataset.signature !== signature) {
            whisperSelect.innerHTML = '';
            (whisper.catalog || []).forEach(item => {
                const option = document.createElement('option');
                option.value = item.size;
                option.textContent = item.size + ' · ~' + item.size_mb + ' MB'
                    + (item.present ? ' ✓' : '') + (item.recommended ? ' ★' : '');
                whisperSelect.appendChild(option);
            });
            whisperSelect.dataset.signature = signature;
        }
        const preferred = (whisper.local_sizes || [])[0] || whisper.default_size;
        if (preferred) whisperSelect.value = preferred;
    }
    const whisperHint = document.getElementById('models-whisper-hint');
    if (whisperHint) {
        const local = (whisper.local_sizes || []);
        whisperHint.textContent = local.length ? t('models.whisperPresent').replace('{list}', local.join(', ')) : '';
    }

    populateModelOptions(models, catalog);
}

async function refreshModels() {
    try {
        const state = await modelsRequest('/api/models');
        renderModels(state);
        return state;
    } catch (e) {
        showToast(t('toast.connError'), 'error');
        return null;
    }
}

async function selectModel(name) {
    try {
        await modelsRequest('/api/models/ollama/active', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: name })
        });
        showToast(t('models.selected').replace('{m}', name), 'success');
        await refreshModels();
        if (typeof refreshSetup === 'function') refreshSetup();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function pullModelByName() {
    const input = document.getElementById('models-name-input');
    const typed = input ? input.value.trim() : '';
    const fallback = (modelsState && modelsState.ollama && modelsState.ollama.model) || '';
    const name = typed || fallback;
    if (!name) { showToast(t('models.needName'), 'error'); return; }
    const button = document.getElementById('models-pull-btn');
    if (button) button.disabled = true;
    try {
        await modelsRequest('/api/models/ollama/pull', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: name, activate: true })
        });
        showToast(t('models.pullStarted').replace('{m}', name), 'info');
        if (input) input.value = '';
        startModelsPolling();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (button) button.disabled = false;
    }
}

async function importModelFromUrl() {
    const urlInput = document.getElementById('models-url-input');
    const nameInput = document.getElementById('models-url-name');
    const url = urlInput ? urlInput.value.trim() : '';
    const name = nameInput ? nameInput.value.trim() : '';
    if (!url) { showToast(t('models.needUrl'), 'error'); return; }
    const button = document.getElementById('models-import-btn');
    if (button) button.disabled = true;
    try {
        const data = await modelsRequest('/api/models/ollama/import', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, name: name })
        });
        showToast(t('models.importStarted').replace('{m}', data.model || name || url), 'info');
        if (urlInput) urlInput.value = '';
        if (nameInput) nameInput.value = '';
        startModelsPolling();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (button) button.disabled = false;
    }
}

async function downloadWhisperFromSettings() {
    const select = document.getElementById('models-whisper-size');
    const size = select ? select.value : '';
    if (!size) return;
    const button = document.getElementById('models-whisper-btn');
    if (button) button.disabled = true;
    try {
        await modelsRequest('/api/models/whisper/download', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ size: size })
        });
        showToast(t('models.whisperStarted'), 'info');
        startModelsPolling();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (button) button.disabled = false;
    }
}

function renderModelsProgress(tasks) {
    const wrap = document.getElementById('models-progress');
    if (!wrap) return;
    const keys = Object.keys(tasks || {});
    const relevant = keys
        .map(key => tasks[key])
        .filter(task => task && (task.label || '').match(/whisper|import|ollama|импорт/i))
        .sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0));
    const task = relevant[0];
    if (!task) { wrap.classList.add('hidden'); return; }
    wrap.classList.remove('hidden');
    const percent = task.status === 'done' ? 100 : (task.progress || 0);
    const bar = document.getElementById('models-progress-bar');
    const label = document.getElementById('models-progress-label');
    const percentLabel = document.getElementById('models-progress-percent');
    if (bar) bar.style.width = percent + '%';
    if (percentLabel) percentLabel.textContent = percent + '%';
    if (label) {
        const name = task.label || '';
        if (task.status === 'error') label.textContent = name + ': ' + (task.error || t('setup.error'));
        else if (task.status === 'done') label.textContent = name + ': ' + t('setup.finished');
        else label.textContent = name + ': ' + (task.status_text || '') +
            (task.downloaded_mb ? ' · ' + task.downloaded_mb + ' / ' + (task.total_mb || '?') + ' MB' : '');
    }
}

function stopModelsPolling() {
    if (modelsPollTimer) {
        clearInterval(modelsPollTimer);
        modelsPollTimer = null;
    }
}

function startModelsPolling() {
    if (modelsPollTimer) return;
    modelsPollTimer = setInterval(async () => {
        let tasks = {};
        try {
            tasks = await modelsRequest('/api/models/tasks');
        } catch (e) {
            return;
        }
        renderModelsProgress(tasks);
        const running = Object.keys(tasks).some(key => tasks[key].status === 'running');
        if (!running) {
            stopModelsPolling();
            await refreshModels();
            if (typeof refreshSetup === 'function') refreshSetup();
        }
    }, 1500);
}

// Периодически обновляем список, пока открыты настройки (модель могли скачать извне)
function scheduleModelsRefresh() {
    if (modelsRefreshTimer) return;
    modelsRefreshTimer = setInterval(() => {
        const settingsView = document.getElementById('view-settings');
        if (settingsView && settingsView.classList.contains('active')) refreshModels();
    }, 20000);
}

refreshModels();
scheduleModelsRefresh();
applyLang();
