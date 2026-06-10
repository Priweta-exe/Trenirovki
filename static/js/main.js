// ============================================
// API
// ============================================

async function api(method, url, body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
    };
    if (body !== null) opts.body = JSON.stringify(body);

    const res = await fetch(url, opts);
    const data = res.status === 204 ? null : await res.json().catch(() => null);

    if (!res.ok) {
        const msg = data?.detail || `Ошибка ${res.status}`;
        throw new Error(Array.isArray(msg) ? msg.map(e => e.msg).join(', ') : msg);
    }
    return data;
}

const get  = (url)         => api('GET',    url);
const post = (url, body)   => api('POST',   url, body);
const patch = (url, body)  => api('PATCH',  url, body);
const del  = (url)         => api('DELETE', url);


// ============================================
// TOAST
// ============================================

function toast(msg, type = '') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const el = document.createElement('div');
    el.className = `toast${type ? ' toast-' + type : ''}`;
    el.textContent = msg;
    container.appendChild(el);

    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transition = 'opacity 300ms';
        setTimeout(() => el.remove(), 300);
    }, 3000);
}

const toastOk  = (msg) => toast(msg, 'success');
const toastErr = (msg) => toast(msg, 'error');


// ============================================
// HELPERS
// ============================================

function difficultyLabel(d) {
    return { beginner: 'начальный', intermediate: 'средний', advanced: 'продвинутый' }[d] || d || '';
}

function setLoading(btn, loading) {
    btn.disabled = loading;
    btn.style.opacity = loading ? '0.6' : '';
}
