"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useConnectors(projectId: string | undefined) {
  return useQuery({
    queryKey: ["connectors", projectId],
    queryFn: () => api.listConnectors(projectId!),
    enabled: !!projectId,
    refetchInterval: 30_000,
  });
}

export function useCreateConnector(projectId: string) {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { provider: string; external_account_id?: string }) =>
      api.createConnector({ tenant_id: session!.tenantId, project_id: projectId, ...body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors", projectId] });
    },
  });
}

export function useRevokeConnector(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectorId: string) => api.revokeConnector(connectorId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors", projectId] });
    },
  });
}

export function useSyncRuns(connectorId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: ["sync-runs", connectorId, projectId],
    queryFn: () => api.listSyncRuns(connectorId!, projectId!),
    enabled: !!connectorId && !!projectId,
  });
}
