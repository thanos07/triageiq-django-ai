"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { apiFetch, clearTokens, getAccessToken, login as apiLogin } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getAccessToken()) {
      setLoading(false);
      return;
    }
    apiFetch<User>("/auth/me/")
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthValue>(() => ({
    user,
    loading,
    login: async (email, password) => {
      const current = await apiLogin(email, password);
      setUser(current);
    },
    logout: () => {
      clearTokens();
      setUser(null);
      window.location.href = "/login";
    },
  }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}
