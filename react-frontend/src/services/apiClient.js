import { authStorage } from '../lib/storage';

function getApiBaseUrl() {
  const configuredUrl = import.meta.env.VITE_API_BASE_URL;
  const frontendHost = window.location.hostname;

  const isFrontendLocal =
    frontendHost === 'localhost' || frontendHost === '127.0.0.1';

  const isConfiguredLocal =
    configuredUrl?.includes('localhost') ||
    configuredUrl?.includes('127.0.0.1');

  if (configuredUrl && (!isConfiguredLocal || isFrontendLocal)) {
    return configuredUrl;
  }

  return `${window.location.protocol}//${frontendHost}:8000`;
}

// const API_BASE_URL = getApiBaseUrl();
const API_BASE_URL = "https://api.autoaudit.asija.cloud";


async function request(
  path,
  {
    method = 'GET',
    body,
    params,
    headers = {},
    isForm = false,
    download = false,
  } = {}
) {
  console.log(API_BASE_URL)
  const url = new URL(path, API_BASE_URL);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, value);
      }
    });
  }

  const auth = authStorage.get();
  const token = auth?.access_token || auth?.token;

  const finalHeaders = { ...headers };

  if (!isForm) {
    finalHeaders['Content-Type'] = 'application/json';
  }

  if (token) {
    finalHeaders.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    method,
    headers: finalHeaders,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `Request failed: ${res.status}`;

    try {
      const err = await res.json();
      detail = err.detail || err.message || detail;
    } catch {
      // Keep default detail.
    }

    throw new Error(Array.isArray(detail) ? detail.join(', ') : detail);
  }

  if (download) return res.blob();

  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const api = {
  get: (path, params) => request(path, { params }),
  post: (path, body) => request(path, { method: 'POST', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  delete: (path, body) => request(path, { method: 'DELETE', body }),
  form: (path, formData) =>
    request(path, { method: 'POST', body: formData, isForm: true }),
  download: (path, params) => request(path, { params, download: true }),
};