/**
 * API base URL for the Django backend (no trailing slash).
 * Set VITE_API_BASE_URL in frontend/.env or window.API_BASE_URL before scripts load.
 * In Vite dev, defaults to same-origin so /api is proxied (see vite.config.js).
 */
const fromVite =
  typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL;

const devSameOrigin =
  typeof import.meta !== 'undefined' && import.meta.env?.DEV && !fromVite;

const browserSameOrigin =
  typeof window !== 'undefined' &&
  window.location &&
  !fromVite &&
  !window.API_BASE_URL;

export const API_BASE_URL = (
  fromVite ||
  window.API_BASE_URL ||
  (devSameOrigin || browserSameOrigin ? '' : 'http://localhost:8000')
).replace(/\/$/, '');

export function apiUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${p}`;
}

window.API_BASE_URL = API_BASE_URL;
window.apiUrl = apiUrl;
window.apiFetch = apiUrl;
