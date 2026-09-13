"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useTenantMembers() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["tenant-members", session?.tenantId],
    queryFn: () => api.listTenantMembers(session!.tenantId),
    enabled: !!session,
  });
}

export function useAddTenantMember() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; role: string }) => api.addTenantMember(session!.tenantId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-members", session?.tenantId] });
    },
  });
}

export function useUpdateTenantMemberRole() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.updateTenantMemberRole(session!.tenantId, userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-members", session?.tenantId] });
    },
  });
}

export function useRemoveTenantMember() {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.removeTenantMember(session!.tenantId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-members", session?.tenantId] });
    },
  });
}

export function useProjectMembers(projectId: string | undefined) {
  return useQuery({
    queryKey: ["project-members", projectId],
    queryFn: () => api.listProjectMembers(projectId!),
    enabled: !!projectId,
  });
}

export function useAddProjectMember(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; role: string }) => api.addProjectMember(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-members", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-overview", projectId] });
    },
  });
}

export function useUpdateProjectMemberRole(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.updateProjectMemberRole(projectId, userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-members", projectId] });
    },
  });
}

export function useRemoveProjectMember(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.removeProjectMember(projectId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-members", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project-overview", projectId] });
    },
  });
}
