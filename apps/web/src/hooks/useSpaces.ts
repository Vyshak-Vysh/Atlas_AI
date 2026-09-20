"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";

export function useSpaces() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["spaces", session?.tenantId],
    queryFn: () => api.listSpaces(session!.tenantId),
    enabled: !!session,
    staleTime: 60_000,
  });
}

export function useSpaceOverview(spaceId: string | undefined) {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["space", spaceId, session?.tenantId],
    queryFn: () => api.getSpaceOverview(spaceId!, session!.tenantId),
    enabled: !!spaceId && !!session,
  });
}

export function useSpaceProjects(spaceId: string | undefined) {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["space-projects", spaceId, session?.tenantId],
    queryFn: () => api.listSpaceProjects(spaceId!, session!.tenantId),
    enabled: !!spaceId && !!session,
  });
}

export function useCreateSpace() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string; color?: string }) =>
      api.createSpace({ tenant_id: session!.tenantId, ...body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["spaces", session?.tenantId] });
    },
  });
}

export function useUpdateSpace(spaceId: string) {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name?: string; description?: string; color?: string; status?: string }) =>
      api.updateSpace(spaceId, session!.tenantId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["spaces", session?.tenantId] });
      queryClient.invalidateQueries({ queryKey: ["space", spaceId, session?.tenantId] });
    },
  });
}

export function useSpaceFindings(spaceId: string | undefined, status?: string) {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["space-findings", spaceId, session?.tenantId, status],
    queryFn: () => api.listSpaceFindings(spaceId!, session!.tenantId, status),
    enabled: !!spaceId && !!session,
  });
}

export function useSpaceActions(spaceId: string | undefined, status?: string) {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["space-actions", spaceId, session?.tenantId, status],
    queryFn: () => api.listSpaceActions(spaceId!, session!.tenantId, status),
    enabled: !!spaceId && !!session,
  });
}

export function useSpaceReport(spaceId: string | undefined) {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["space-report", spaceId, session?.tenantId],
    queryFn: () => api.getSpaceReport(spaceId!, session!.tenantId),
    enabled: !!spaceId && !!session,
  });
}

export function useDeleteSpace() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (spaceId: string) => api.deleteSpace(spaceId, session!.tenantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["spaces", session?.tenantId] });
    },
  });
}
