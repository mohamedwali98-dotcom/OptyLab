/**
 * backend.js — resolves the base URL for the OptyLab Python backend.
 *
 * The backend ALWAYS runs on port 8000 (do not change). The FRONTEND may be
 * opened in three ways:
 *   1. http://localhost:5173        → backend is http://localhost:8000   (dev)
 *   2. http://192.168.1.x:5173      → backend is http://192.168.1.x:8000  (LAN/phone)
 *   3. https://myhost.example.com   → backend is https://myhost.example.com:8000 (deployed)
 *
 * We derive the backend host from the current page's host so the request always
 * targets the SAME origin family. This fixes the "Backend offline" error that
 * occurs when the site is opened via a Network IP or https but the code still
 * points at a hardcoded http://localhost:8000 (mixed content / origin mismatch).
 *
 * Override with VITE_API_URL if you need a fixed backend location.
 */

export function resolveBackendUrl() {
  const override = import.meta.env.VITE_API_URL;
  if (override) return override.replace(/\/$/, '');

  const { protocol, hostname } = window.location;
  // In production builds served FROM the backend (same host, different path) you
  // could use '' — but OptyLab serves the dev server and the API on the same host
  // at different ports, so we keep the page's hostname and switch the port to 8000.
  return `${protocol}//${hostname}:8000`;
}

export const BACKEND_URL = resolveBackendUrl();
