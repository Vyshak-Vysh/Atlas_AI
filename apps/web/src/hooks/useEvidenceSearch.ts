"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useEvidenceSearch(projectId: string | undefined, query: string, topN = 20) {
  return useQuery({
    queryKey: ["evidence-search", projectId, query, topN],
    queryFn: () => api.searchEvidence(projectId!, query, topN),
    enabled: !!projectId && query.trim().length > 0,
    staleTime: 30_000,
  });
}
