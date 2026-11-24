import { reactive } from 'vue';
import { api } from './api';

// Аутентификация на HttpOnly-куке: токен в JS недоступен.
// authState.user — только для отображения; источник истины — сервер.
export const authState = reactive({
  user: null,
  loading: false,
  initialized: false, // выполнено ли восстановление сессии
  error: null,
});

export function isAuthenticated() {
  return !!authState.user;
}

export async function login(username, password, captcha = {}) {
  authState.error = null;
  const user = await api.login({
    username,
    password,
    captcha_token: captcha.token ?? null,
    captcha_answer: captcha.answer ?? null,
    captcha_honeypot: captcha.honeypot ?? null,
  });
  authState.user = user;
  authState.initialized = true;
  return user;
}

export async function register(payload) {
  authState.error = null;
  const user = await api.register(payload);
  authState.user = user;
  authState.initialized = true;
  return user;
}

export async function logout() {
  try {
    await api.logout();
  } finally {
    authState.user = null;
  }
}

// Восстановление сессии по куке при старте приложения.
export async function restoreSession() {
  if (authState.initialized) return authState.user;
  authState.loading = true;
  try {
    authState.user = await api.me();
  } catch {
    authState.user = null;
  } finally {
    authState.loading = false;
    authState.initialized = true;
  }
  return authState.user;
}
