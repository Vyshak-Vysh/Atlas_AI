"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useAuditEvents(limit = 100) {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["audit-events", session?.tenantId, limit],
    queryFn: () => api.listAuditEvents(session!.tenantId, limit),
    enabled: !!session,
    refetchInterval: 30_000,
  });
}
