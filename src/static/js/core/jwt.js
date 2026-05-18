// JWT service: single source of truth for tokens and user
import { STORAGE_KEYS, API_PREFIX, ROUTES } from './config.js';

function getItem(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}
function setItem(key, value) {
  try { localStorage.setItem(key, value); } catch {}
}
function removeItem(key) {
  try { localStorage.removeItem(key); } catch {}
}

export const JWT = {
  getAccessToken() { return null; },
  getRefreshToken() { return null; },
  getUser() {
    const raw = getItem(STORAGE_KEYS.currentUser);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  },
  setTokens() {
    removeItem(STORAGE_KEYS.accessToken);
    removeItem(STORAGE_KEYS.refreshToken);
  },
  setUser(user) {
    if (user) setItem(STORAGE_KEYS.currentUser, JSON.stringify(user));
  },
  clear() {
    removeItem(STORAGE_KEYS.accessToken);
    removeItem(STORAGE_KEYS.refreshToken);
    removeItem(STORAGE_KEYS.currentUser);
  },
  isAuthenticated() { return !!this.getUser(); },
  async refresh() {
    try {
      const res = await fetch('/refresh', {
        method: 'POST',
        credentials: 'same-origin',
      });
      if (!res.ok) return null;
      const data = await res.json();
      if (data?.success) {
        if (data.user) this.setUser(data.user);
        return true;
      }
    } catch {}
    return null;
  },
  requireAuthOrRedirect() {
    if (!this.isAuthenticated()) {
      window.location.href = ROUTES.login;
      return false;
    }
    return true;
  },
  requireAdminOrRedirect() {
    const user = this.getUser();
    if (!this.isAuthenticated() || !user || user.role !== 'admin') {
      window.location.href = ROUTES.home;
      return false;
    }
    return true;
  },
};
