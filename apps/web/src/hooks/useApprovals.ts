"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";

export function useActions(projectId: string | undefined, status?: string) {
  return useQuery({
    queryKey: ["actions", projectId, status],
    queryFn: () => api.listActions(projectId!, status),
    enabled: !!projectId,
    refetchInterval: 15_000,
  });
}

export function useAction(actionId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: ["action", actionId, projectId],
    queryFn: () => api.getAction(actionId!, projectId!),
    enabled: !!actionId && !!projectId,
    refetchInterval: (query) => (query.state.data?.status === "WAITING_APPROVAL" ? 10_000 : false),
  });
}

export function useApproveAction(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ actionId, reason, expectedPayloadHash }: { actionId: string; reason?: string; expectedPayloadHash?: string }) =>
      api.approveAction(actionId, projectId, { reason, expected_payload_hash: expectedPayloadHash }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["actions", projectId] });
      queryClient.invalidateQueries({ queryKey: ["action", variables.actionId, projectId] });
      queryClient.invalidateQueries({ queryKey: ["findings", projectId] });
    },
  });
}

export function useRejectAction(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ actionId, reason }: { actionId: string; reason?: string }) =>
      api.rejectAction(actionId, projectId, { reason }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["actions", projectId] });
      queryClient.invalidateQueries({ queryKey: ["action", variables.actionId, projectId] });
    },
  });
}

export function actionErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (error.status === 409) return "This action's state changed since you loaded it — refresh and try again.";
    if (error.status === 410) return "The approval window for this action has expired.";
  }
  return "The request could not be completed.";
}
