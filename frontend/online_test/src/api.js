// Базовый URL API. В dev запросы идут через vite-прокси по относительному пути,
// поэтому оставляем пустым (same-origin) — это нужно для HttpOnly-кук.
const BASE_URL = '';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...options,
  });

  // Если access-токен истёк (401) — один раз пробуем обновить сессию по
  // refresh-куке и повторить исходный запрос (кроме самих auth-эндпоинтов).
  if (res.status === 401 && !options._retry && !_isAuthPath(path)) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return request(path, { ...options, _retry: true });
    }
  }

  if (res.status === 204) return null;

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const err = new Error(_extractErrorMessage(data, res.status));
    err.status = res.status;
    err.data = data;
    // Для 429 сервер присылает Retry-After (сек) — клиент может показать
    // таймер и разблокировать кнопку точно к моменту снятия лимита.
    const retryAfter = Number(res.headers.get('Retry-After'));
    if (Number.isFinite(retryAfter) && retryAfter > 0) err.retryAfter = retryAfter;
    throw err;
  }

  return data;
}

// На эндпоинтах авторизации «рефреш» не нужен и может сломать логику.
function _isAuthPath(path) {
  return path.startsWith('/api/auth/login')
    || path.startsWith('/api/auth/register')
    || path.startsWith('/api/auth/refresh')
    || path.startsWith('/api/auth/logout');
}

let _refreshPromise = null;

// Единый «рефреш» с дедупликацией: параллельные 401 не порождают шторм запросов.
function tryRefresh() {
  if (_refreshPromise) return _refreshPromise;
  _refreshPromise = fetch(`${BASE_URL}/api/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      _refreshPromise = null;
    });
  return _refreshPromise;
}

// Превращаем ответ об ошибке FastAPI в читаемую строку.
// detail может быть: строкой, массивом ошибок валидации (422) или объектом.
function _extractErrorMessage(data, status) {
  if (data && typeof data === 'object') {
    const detail = data.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const msgs = detail.map((d) => {
        if (typeof d === 'string') return d;
        if (d && typeof d === 'object') {
          const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : '';
          return field ? `${field}: ${d.msg}` : d.msg;
        }
        return String(d);
      });
      return msgs.join('; ') || `Ошибка ${status}`;
    }
    if (detail && typeof detail === 'object') {
      return detail.msg || JSON.stringify(detail);
    }
  }
  if (typeof data === 'string' && data) return data;
  return `Ошибка ${status}`;
}

async function downloadFile(path) {
  let res = await fetch(`${BASE_URL}${path}`, { credentials: 'include' });
  // Истёк access-токен — обновляем сессию и повторяем выгрузку.
  if (res.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      res = await fetch(`${BASE_URL}${path}`, { credentials: 'include' });
    }
  }
  if (!res.ok) {
    let message = 'Ошибка выгрузки';
    try {
      const data = await res.json();
      if (typeof data?.detail === 'string') message = data.detail;
    } catch { /* ignore */ }
    throw new Error(message);
  }
  const blob = await res.blob();
  let filename = 'export.xlsx';
  const cd = res.headers.get('Content-Disposition') || '';
  const m = cd.match(/filename="?([^"]+)"?/);
  if (m) filename = m[1];

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  // auth
  login: (payload) => request('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  register: (payload) => request('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  me: () => request('/api/auth/me'),
  deleteMe: () => request('/api/auth/me', { method: 'DELETE' }),

  // tests
  myTests: () => request('/api/tests'),
  getTest: (id) => request(`/api/tests/${id}`),
  saveTest: (payload) => request('/api/tests', { method: 'POST', body: JSON.stringify(payload) }),
  updateTest: (id, payload) => request(`/api/tests/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  publishTest: (id) => request(`/api/tests/${id}/publish`, { method: 'POST' }),
  unpublishTest: (id) => request(`/api/tests/${id}/unpublish`, { method: 'POST' }),
  deleteTest: (id) => request(`/api/tests/${id}`, { method: 'DELETE' }),

  // attempts / results
  testAttempts: (id) => request(`/api/tests/${id}/attempts`),
  attemptDetail: (id, attemptId) => request(`/api/tests/${id}/attempts/${attemptId}`),
  exportAttempts: (id) => downloadFile(`/api/tests/${id}/attempts/export`),

  // public (прохождение по ссылке)
  getPublicTest: (token) => request(`/api/public/tests/${token}`),
  submitAttempt: (token, payload) => request(`/api/public/tests/${token}/submit`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  // media (изображения к вопросам)
  // multipart: Content-Type выставляет браузер сам (с boundary),
  // поэтому заголовок из request() убираем.
  uploadMedia: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/api/media', {
      method: 'POST',
      body: form,
      headers: {},
    });
  },
  deleteMedia: (id) => request(`/api/media/${id}`, { method: 'DELETE' }),
  mediaUrl: (id) => `${BASE_URL}/api/media/${id}`,

  // admin
  adminTests: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set('q', params.q);
    if (params.status) qs.set('status', params.status);
    if (params.author_id) qs.set('author_id', params.author_id);
    const s = qs.toString();
    return request(`/api/admin/tests${s ? `?${s}` : ''}`);
  },
  adminUsers: () => request('/api/admin/users'),
  adminSetUserActive: (id, isActive) => request(`/api/admin/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  }),
  adminSetApproval: (id, approvalStatus) => request(`/api/admin/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ approval_status: approvalStatus }),
  }),
  adminDeleteUser: (id) => request(`/api/admin/users/${id}`, { method: 'DELETE' }),
};
