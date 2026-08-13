/**
 * api.js — thin fetch wrapper for the OptyLab backend.
 *
 * Stores the JWT bearer token in localStorage under "optylab-token" and attaches
 * it automatically to every request. Endpoints that don't need auth simply won't
 * send one.
 */

import { BACKEND_URL } from './backend';

const TOKEN_KEY = 'optylab-token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || null;
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

let onUnauthorizedCallback = null;

export function onUnauthorized(cb) {
  onUnauthorizedCallback = cb;
}

async function request(method, path, body) {
  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let res;
  try {
    res = await fetch(`${BACKEND_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new ApiError('Cannot connect to the server. Is the backend running?', 0, null);
  }

  let data = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }

  if (!res.ok) {
    if (res.status === 401 && path !== '/auth/login' && path !== '/auth/register') {
      clearToken();
      if (onUnauthorizedCallback) onUnauthorizedCallback();
    }
    const detail = (data && data.detail) || `Request failed (${res.status})`;
    throw new ApiError(detail, res.status, data);
  }
  return data;
}

export const api = {
  register: (email, name, password) => request('POST', '/auth/register', { email, name, password }),
  login:    (email, password)       => request('POST', '/auth/login',    { email, password }),
  me:       ()                      => request('GET',  '/auth/me'),
  changePassword: (old_password, new_password) =>
    request('POST', '/auth/change-password', { old_password, new_password }),
  history:  ()                      => request('GET',  '/auth/history'),
  processed: ()                     => request('GET',  '/auth/processed'),
  adminAccessList: ()               => request('GET',  '/auth/admin-access'),
  grantAccess:  (email)             => request('POST', '/auth/admin-access', { email }),
  revokeAccess: (email)             => request('DELETE', '/auth/admin-access', { email }),
  clearUploads: ()                  => request('DELETE', '/clear-uploads'),
};

export { ApiError };
