// ==================== ОЧЕРЕДЬ И ТОЧНОСТЬ НАРЕЗКИ ====================
// Пауза/продолжение очереди, индикатор состояния и переключатель точной нарезки.
Object.assign(I18N.ru, {
    'queue.title': 'Очередь и точность',
    'queue.accurate': 'Точная нарезка (медленнее, но без сдвига границ)',
    'queue.pause': 'Пауза очереди', 'queue.resume': 'Продолжить',
    'queue.paused': 'Очередь на паузе', 'queue.active': 'Активных: {a}, в очереди: {q}',
    'queue.pauseToast': 'Очередь приостановлена', 'queue.resumeToast': 'Очередь продолжена'
});
Object.assign(I18N.en, {
    'queue.title': 'Queue & precision',
    'queue.accurate': 'Accurate cutting (slower, no boundary drift)',
    'queue.pause': 'Pause queue', 'queue.resume': 'Resume',
    'queue.paused': 'Queue paused', 'queue.active': 'Active: {a}, queued: {q}',
    'queue.pauseToast': 'Queue paused', 'queue.resumeToast': 'Queue resumed'
});

const ACCURATE_KEY = 'accurate_cut';

function initAccurateToggle() {
    const box = document.getElementById('set-accurate');
    if (!box) return;
    const stored = localStorage.getItem(ACCURATE_KEY);
    box.checked = stored === null ? true : stored === '1';
    box.addEventListener('change', () => localStorage.setItem(ACCURATE_KEY, box.checked ? '1' : '0'));
}

// script.js собирает FormData сам, поэтому добавляем поле перед отправкой
const __cutlineFetch = window.fetch.bind(window);
window.fetch = function (url, options) {
    const isProcess = (typeof url === 'string' && url.indexOf('/process') === 0)
        || (url && url.url && String(url.url).indexOf('/process') === 0);
    const body = options && options.body;
    if (isProcess && body && typeof body.append === 'function' && !(body instanceof URLSearchParams)) {
        const box = document.getElementById('set-accurate');
        const value = box ? (box.checked ? '1' : '0') : (localStorage.getItem(ACCURATE_KEY) === '0' ? '0' : '1');
        try { body.append('accurate_cut', value); } catch (e) { /* уже есть - не страшно */ }
    }
    return __cutlineFetch(url, options);
};

async function refreshQueueStatus() {
    const label = document.getElementById('queue-status-text');
    if (!label) return;
    try {
        const response = await fetch('/api/queue');
        const data = await response.json();
        label.textContent = data.paused
            ? t('queue.paused')
            : t('queue.active').replace('{a}', data.active).replace('{q}', data.queued);
        label.className = 'badge ' + (data.paused ? 'badge--warn' : 'badge--accent');
    } catch (e) { /* сервер недоступен - оставляем прежний текст */ }
}

async function queueRequest(path) {
    const response = await fetch(path, { method: 'POST' });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return response.json();
}

async function pauseQueue() {
    try {
        await queueRequest('/api/queue/pause');
        showToast(t('queue.pauseToast'), 'info');
    } catch (e) {
        showToast(e.message, 'error');
    }
    refreshQueueStatus();
}

async function resumeQueue() {
    try {
        await queueRequest('/api/queue/resume');
        showToast(t('queue.resumeToast'), 'success');
    } catch (e) {
        showToast(e.message, 'error');
    }
    refreshQueueStatus();
}

initAccurateToggle();
applyLang();
refreshQueueStatus();
setInterval(refreshQueueStatus, 5000);
