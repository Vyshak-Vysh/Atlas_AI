"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { MembershipRole } from "@/lib/types";

export function useCurrentTenant() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["tenant", session?.tenantId],
    queryFn: () => api.getTenant(session!.tenantId),
    enabled: !!session,
    staleTime: 60_000,
  });
}

export function useMyTenants() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["my-tenants", session?.userId],
    queryFn: () => api.listMyTenants(),
    enabled: !!session,
    staleTime: 60_000,
  });
}

/** The caller's role within the current tenant, derived from the tenant
 * membership list rather than decoding the JWT client-side — the backend
 * remains the authority; this is only used to toggle UI affordances. */
export function useCurrentRole(): MembershipRole | undefined {
  const { session } = useAuth();
  const { data } = useMyTenants();
  const membership = data?.find((m) => m.tenant_id === session?.tenantId);
  return membership?.role as MembershipRole | undefined;
}
