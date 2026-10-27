// ==================== ПРЕСЕТЫ (сервер) + ZIP-ЭКСПОРТ ====================
// Пресеты хранятся в файле на сервере (переносятся между браузерами),
// старые пресеты из localStorage переносятся автоматически при первом запуске.
Object.assign(I18N.ru, {
    'presets.export': 'Экспорт', 'presets.import': 'Импорт',
    'presets.saved': 'Пресет сохранён', 'presets.imported': 'Пресеты импортированы',
    'presets.deleted': 'Пресет удалён', 'presets.exportEmpty': 'Нет пресетов для экспорта'
});
Object.assign(I18N.en, {
    'presets.export': 'Export', 'presets.import': 'Import',
    'presets.saved': 'Preset saved', 'presets.imported': 'Presets imported',
    'presets.deleted': 'Preset deleted', 'presets.exportEmpty': 'No presets to export'
});

let serverPresets = {};

// Переопределяет localStorage-версию из script.js
function getPresets() { return serverPresets; }

async function presetsRequest(url, options) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    return data;
}

async function loadPresets() {
    try {
        const data = await presetsRequest('/api/presets');
        serverPresets = data.presets || {};
    } catch (e) {
        return;
    }
    await migrateLocalPresets();
    renderPresets();
}

async function migrateLocalPresets() {
    const raw = localStorage.getItem('filter_presets');
    if (!raw) return;
    let local = {};
    try { local = JSON.parse(raw) || {}; } catch (e) { local = {}; }
    const names = Object.keys(local);
    for (const name of names) {
        if (serverPresets[name]) continue;
        const entry = local[name];
        const words = Array.isArray(entry) ? entry : (entry.words || []);
        const settings = Array.isArray(entry) ? {} : (entry.settings || {});
        if (!words.length) continue;
        try {
            await presetsRequest('/api/presets', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, entry: { words: words, settings: settings } })
            });
        } catch (e) { return; }
    }
    localStorage.removeItem('filter_presets');
}

function currentPresetSettings() {
    const modeInput = document.querySelector('input[name="mode"]:checked');
    return {
        mode: modeInput ? modeInput.value : 'remove',
        padding: document.getElementById('set-padding').value,
        freq: document.getElementById('set-freq').value,
        gain: document.getElementById('set-gain').value,
        format: document.getElementById('set-format').value,
        language: document.getElementById('set-language').value,
        model_size: document.getElementById('set-model-size').value,
        stem: document.getElementById('set-stem').checked,
        mute: document.getElementById('set-mute').checked
    };
}

async function saveCurrentPreset() {
    const input = document.getElementById('new-preset-name');
    if (!tags.length) { showToast(t('toast.noWords'), 'error'); return; }
    const name = input.value.trim() || ('Preset ' + (Object.keys(serverPresets).length + 1));
    try {
        await presetsRequest('/api/presets', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, entry: { words: tags, settings: currentPresetSettings() } })
        });
        input.value = '';
        await loadPresets();
        showToast(t('presets.saved') + ': ' + name, 'success');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function deletePreset(name) {
    try {
        await presetsRequest('/api/presets/' + encodeURIComponent(name), { method: 'DELETE' });
        await loadPresets();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function exportPresets() {
    if (!Object.keys(serverPresets).length) { showToast(t('presets.exportEmpty'), 'info'); return; }
    window.location.href = '/api/presets/export';
}

async function importPresets(input) {
    const file = input.files && input.files[0];
    if (!file) return;
    try {
        const text = await file.text();
        const data = JSON.parse(text);
        const presets = data.presets || data;
        await presetsRequest('/api/presets/import', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ presets: presets })
        });
        await loadPresets();
        showToast(t('presets.imported'), 'success');
    } catch (e) {
        showToast(e.message, 'error');
    }
    input.value = '';
}

// ZIP со всеми результатами задачи: кнопка в блоке результатов
document.addEventListener('DOMContentLoaded', () => {
    const zipButton = document.getElementById('btn-download-zip');
    if (!zipButton) return;
    zipButton.addEventListener('click', event => {
        event.preventDefault();
        if (typeof currentTaskId === 'undefined' || !currentTaskId) return;
        window.location.href = '/api/export/' + currentTaskId;
    });
});

applyLang();
loadPresets();
