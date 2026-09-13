"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useSources(projectId: string | undefined) {
  return useQuery({
    queryKey: ["sources", projectId],
    queryFn: () => api.listSources(projectId!),
    enabled: !!projectId,
    refetchInterval: 20_000,
  });
}

export function useUploadDocument(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, visibility }: { file: File; visibility?: string }) =>
      api.uploadDocument(projectId, file, visibility),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", projectId] });
      queryClient.invalidateQueries({ queryKey: ["connectors", projectId] });
    },
  });
}

export function useDeleteSource(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => api.deleteSource(sourceId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", projectId] });
    },
  });
}
