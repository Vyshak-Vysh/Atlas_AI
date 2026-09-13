"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useCurrentUser() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["me", session?.userId],
    queryFn: () => api.getMe(),
    enabled: !!session,
    staleTime: 60_000,
  });
}
