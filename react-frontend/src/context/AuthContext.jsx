import { createContext, useContext, useMemo, useState } from "react";
import { authStorage } from "../lib/storage";
import * as authService from "../services/authService";
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => authStorage.get());
  async function signIn(name, password) {
    const next = await authService.login({ name, password });
    setAuth(next);
    return next;
  }
  async function signOut() {
    await authService.logout();
    setAuth(null);
  }
  const value = useMemo(
    () => ({
      auth,
      user: auth,
      isAuthenticated: !!auth?.access_token,
      signIn,
      signOut,
    }),
    [auth],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
