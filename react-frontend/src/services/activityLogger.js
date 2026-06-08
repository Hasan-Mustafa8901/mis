import { api } from './apiClient';

const isDev = import.meta.env.DEV;

const sanitizeDetails = (details = {}) => {
  const blockedKeys = [
    'password',
    'token',
    'access_token',
    'refresh_token',
    'authorization',
  ];

  const output = {};

  Object.entries(details || {}).forEach(([key, value]) => {
    const lowerKey = String(key).toLowerCase();

    if (blockedKeys.some((blocked) => lowerKey.includes(blocked))) {
      output[key] = '[REDACTED]';
      return;
    }

    output[key] = value;
  });

  return output;
};

export async function logActivity(action, details = {}) {
  const payload = {
    action,
    page: window.location.pathname,
    details: sanitizeDetails(details),
    userAgent: navigator.userAgent,
    timestamp: new Date().toISOString(),
  };

  if (isDev) {
    console.groupCollapsed(
      `%cUSER ACTIVITY%c ${action}`,
      'color:#f59e0b;font-weight:900;',
      'color:#94a3b8;font-weight:700;'
    );
    console.log(payload);
    console.groupEnd();
  }

  try {
    await api.post('/activity-logs', payload);
  } catch (error) {
    if (isDev) {
      console.warn('Activity log failed:', error);
    }
  }
}