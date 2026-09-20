"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useSprints(projectId: string | undefined) {
  return useQuery({
    queryKey: ["sprints", projectId],
    queryFn: () => api.listSprints(projectId!),
    enabled: !!projectId,
  });
}

export function useSprint(projectId: string | undefined, sprintId: string | undefined) {
  return useQuery({
    queryKey: ["sprint", projectId, sprintId],
    queryFn: () => api.getSprint(projectId!, sprintId!),
    enabled: !!projectId && !!sprintId,
  });
}

export function useCreateSprint(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; sprint_number: number; start_date?: string; end_date?: string }) =>
      api.createSprint(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sprints", projectId] });
    },
  });
}

export function useUpdateSprint(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sprintId,
      ...body
    }: {
      sprintId: string;
      name?: string;
      start_date?: string;
      end_date?: string;
      status?: string;
    }) => api.updateSprint(projectId, sprintId, body),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["sprints", projectId] });
      queryClient.invalidateQueries({ queryKey: ["sprint", projectId, variables.sprintId] });
    },
  });
}
