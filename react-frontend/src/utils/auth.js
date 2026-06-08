import { getStoredPageAccess } from '../config/pageAccess';

export function decodeJwt(token) {
  try {
    if (!token) return null;

    const payload = token.split('.')[1];
    if (!payload) return null;

    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const paddedBase64 = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    const decoded = JSON.parse(window.atob(paddedBase64));

    return decoded;
  } catch (error) {
    console.error('TOKEN DECODE ERROR:', error);
    return null;
  }
}

export function tokenIsValid(token) {
  try {
    if (!token) return false;

    const payload = decodeJwt(token);

    // Some existing backend tokens may not have exp.
    // Treat such tokens as valid so frontend does not enter a logout loop.
    if (!payload?.exp) return true;

    const now = Math.floor(Date.now() / 1000);
    return Number(payload.exp) > now;
  } catch (error) {
    console.error('TOKEN ERROR:', error);
    return false;
  }
}

export function getUserRoles(auth) {
  const token = auth?.access_token || auth?.token;
  const payload = decodeJwt(token);

  const roleFromPayload =
    payload?.role ||
    payload?.roles ||
    payload?.user_role ||
    auth?.role ||
    auth?.roles ||
    auth?.user?.role ||
    auth?.user?.roles;

  if (!roleFromPayload) return [];

  if (Array.isArray(roleFromPayload)) {
    return roleFromPayload.map((role) => String(role).toLowerCase());
  }

  return [String(roleFromPayload).toLowerCase()];
}

export function hasAllowedRole(auth, allowedRoles = []) {
  const token = auth?.access_token || auth?.token;

  if (!tokenIsValid(token)) return false;

  const userRoles = getUserRoles(auth);

  if (!allowedRoles.length) return true;

  const normalisedAllowedRoles = allowedRoles.map((role) =>
    String(role).toLowerCase()
  );

  return userRoles.some((role) => normalisedAllowedRoles.includes(role));
}

export function getAllowedRolesForPath(path) {
  const access = getStoredPageAccess();
  return access[path] || [];
}

export function hasPageAccess(auth, path) {
  const allowedRoles = getAllowedRolesForPath(path);
  return hasAllowedRole(auth, allowedRoles);
}
