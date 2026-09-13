"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useAgentRuns(projectId: string | undefined) {
  return useQuery({
    queryKey: ["agent-runs", projectId],
    queryFn: () => api.listAgentRuns(projectId!),
    enabled: !!projectId,
    refetchInterval: 15_000,
  });
}

export function useAgentRun(runId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: ["agent-run", runId, projectId],
    queryFn: () => api.getAgentRun(runId!, projectId!),
    enabled: !!runId && !!projectId,
    refetchInterval: (query) =>
      query.state.data && ["RECEIVED", "RUNNING", "WAITING_APPROVAL"].includes(query.state.data.status)
        ? 3000
        : false,
  });
}

export function useCreateAgentRun(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (question: string) => api.createAgentRun(projectId, question),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-runs", projectId] });
    },
  });
}
