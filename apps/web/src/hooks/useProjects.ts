"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useProjects() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["projects", session?.tenantId],
    queryFn: () => api.listProjects(session!.tenantId),
    enabled: !!session,
  });
}

export function useCreateProject() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; client_name?: string; code?: string }) =>
      api.createProject({ tenant_id: session!.tenantId, ...body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", session?.tenantId] });
    },
  });
}

export function useProjectOverview(projectId: string | undefined) {
  return useQuery({
    queryKey: ["project-overview", projectId],
    queryFn: () => api.getProjectOverview(projectId!),
    enabled: !!projectId,
    refetchInterval: 30_000,
  });
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name?: string; client_name?: string; status?: string }) =>
      api.updateProject(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-overview", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useCreatePhase(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; phase_number: number; start_date?: string; end_date?: string }) =>
      api.createPhase(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-overview", projectId] });
    },
  });
}

export function useProjectReport(projectId: string | undefined) {
  return useQuery({
    queryKey: ["project-report", projectId],
    queryFn: () => api.getProjectReport(projectId!),
    enabled: !!projectId,
  });
}
