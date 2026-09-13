"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useRequirements(projectId: string | undefined, status?: string, phaseId?: string) {
  return useQuery({
    queryKey: ["requirements", projectId, status, phaseId],
    queryFn: () => api.listRequirements(projectId!, status, phaseId),
    enabled: !!projectId,
  });
}

export function useRequirement(requirementId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: ["requirement", requirementId, projectId],
    queryFn: () => api.getRequirement(requirementId!, projectId!),
    enabled: !!requirementId && !!projectId,
  });
}

export function useCreateRequirement(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { key: string; title: string; status: string; phase_id?: string; description?: string }) =>
      api.createRequirement(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requirements", projectId] });
    },
  });
}
