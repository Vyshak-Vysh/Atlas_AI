"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { api } from "./api";
import { clearSession, loadSession, saveSession, type StoredSession } from "./auth-storage";

interface AuthContextValue {
  session: StoredSession | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (tenantName: string, email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  switchTenant: (tenantId: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const queryClient = useQueryClient();

  useEffect(() => {
    setSession(loadSession());
    setLoading(false);

    function onStorage(e: StorageEvent) {
      if (e.key?.startsWith("atlasai.")) setSession(loadSession());
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const body = await api.login({ email, password });
      if (!body.tenant_id) throw new Error("Account has no tenant membership.");
      const next: StoredSession = {
        accessToken: body.access_token,
        refreshToken: body.refresh_token,
        tenantId: body.tenant_id,
        userId: body.user_id,
      };
      saveSession(next);
      setSession(next);
      router.push("/app/overview");
    },
    [router],
  );

  const register = useCallback(
    async (tenantName: string, email: string, password: string, displayName: string) => {
      const body = await api.register({ tenant_name: tenantName, email, password, display_name: displayName });
      if (!body.tenant_id) throw new Error("Registration did not return a tenant.");
      const next: StoredSession = {
        accessToken: body.access_token,
        refreshToken: body.refresh_token,
        tenantId: body.tenant_id,
        userId: body.user_id,
      };
      saveSession(next);
      setSession(next);
      router.push("/app/overview");
    },
    [router],
  );

  const logout = useCallback(async () => {
    const current = loadSession();
    if (current) {
      try {
        await api.logout(current.refreshToken);
      } catch {
        // best-effort: still clear local session even if the API call fails
      }
    }
    clearSession();
    setSession(null);
    queryClient.clear();
    router.push("/login");
  }, [router, queryClient]);

  const switchTenant = useCallback(
    async (tenantId: string) => {
      const body = await api.switchTenant(tenantId);
      if (!body.tenant_id) return;
      const next: StoredSession = {
        accessToken: body.access_token,
        refreshToken: body.refresh_token,
        tenantId: body.tenant_id,
        userId: body.user_id,
      };
      saveSession(next);
      setSession(next);
      queryClient.clear();
      router.push("/app/overview");
    },
    [router, queryClient],
  );

  return (
    <AuthContext.Provider value={{ session, loading, login, register, logout, switchTenant }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
