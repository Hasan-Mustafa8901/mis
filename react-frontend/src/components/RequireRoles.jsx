import { authStorage } from '../lib/storage';
import { hasPageAccess } from '../utils/auth';

export default function RequireRoles({ path, children }) {
  const auth = authStorage.get();
  const allowed = hasPageAccess(auth, path || window.location.pathname);

  if (!allowed) {
    if (window.location.pathname !== '/') {
      window.history.replaceState({}, '', '/');
      window.location.reload();
    }

    return null;
  }

  return children;
}
