"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useFindings(projectId: string | undefined, status?: string) {
  return useQuery({
    queryKey: ["findings", projectId, status],
    queryFn: () => api.listFindings(projectId!, status),
    enabled: !!projectId,
    refetchInterval: 20_000,
  });
}

export function useFinding(findingId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: ["finding", findingId, projectId],
    queryFn: () => api.getFinding(findingId!, projectId!),
    enabled: !!findingId && !!projectId,
  });
}
