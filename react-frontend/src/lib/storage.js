const AUTH_KEY = 'auth';
const LEGACY_KEYS = ['mis_auth'];

export const authStorage = {
  get() {
    try {
      const current = localStorage.getItem(AUTH_KEY);
      if (current) return JSON.parse(current);

      for (const key of LEGACY_KEYS) {
        const legacy = localStorage.getItem(key);
        if (legacy) {
          const parsed = JSON.parse(legacy);
          localStorage.setItem(AUTH_KEY, JSON.stringify(parsed));
          return parsed;
        }
      }

      return null;
    } catch {
      return null;
    }
  },

  set(value) {
    localStorage.setItem(AUTH_KEY, JSON.stringify(value));
    LEGACY_KEYS.forEach((key) => localStorage.removeItem(key));
  },

  clear() {
    localStorage.removeItem(AUTH_KEY);
    LEGACY_KEYS.forEach((key) => localStorage.removeItem(key));
  },
};
