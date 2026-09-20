"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface RequirementFilters {
  status?: string;
  phaseId?: string;
  taskStatus?: string;
  priority?: string;
  assigneeId?: string;
  sprintId?: string;
}

export function useRequirements(projectId: string | undefined, filters?: RequirementFilters) {
  return useQuery({
    queryKey: ["requirements", projectId, filters],
    queryFn: () => api.listRequirements(projectId!, filters),
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
    mutationFn: (body: {
      key: string;
      title: string;
      status: string;
      phase_id?: string;
      sprint_id?: string;
      description?: string;
      task_status?: string;
      priority?: string;
      due_date?: string;
      assignee_id?: string;
    }) => api.createRequirement(projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requirements", projectId] });
    },
  });
}

export function useUpdateRequirement(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      requirementId,
      ...body
    }: {
      requirementId: string;
      title?: string;
      description?: string | null;
      status?: string;
      phase_id?: string | null;
      sprint_id?: string | null;
      acceptance_criteria?: unknown[];
      task_status?: string;
      priority?: string;
      due_date?: string | null;
      assignee_id?: string | null;
    }) => api.updateRequirement(requirementId, projectId, body),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["requirements", projectId] });
      queryClient.invalidateQueries({ queryKey: ["requirement", variables.requirementId, projectId] });
      queryClient.invalidateQueries({ queryKey: ["requirement-history", variables.requirementId, projectId] });
    },
  });
}

export function useDeleteRequirement(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (requirementId: string) => api.deleteRequirement(requirementId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requirements", projectId] });
    },
  });
}

export function useRequirementComments(requirementId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: ["requirement-comments", requirementId, projectId],
    queryFn: () => api.listRequirementComments(requirementId!, projectId!),
    enabled: !!requirementId && !!projectId,
  });
}

export function useAddRequirementComment(requirementId: string, projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => api.addRequirementComment(requirementId, projectId, { body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requirement-comments", requirementId, projectId] });
    },
  });
}

export function useUpdateRequirementComment(requirementId: string, projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId, body }: { commentId: string; body: string }) =>
      api.updateRequirementComment(requirementId, commentId, projectId, { body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requirement-comments", requirementId, projectId] });
    },
  });
}

export function useDeleteRequirementComment(requirementId: string, projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) => api.deleteRequirementComment(requirementId, commentId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requirement-comments", requirementId, projectId] });
    },
  });
}

export function useRequirementHistory(requirementId: string | undefined, projectId: string | undefined) {
  return useQuery({
    queryKey: ["requirement-history", requirementId, projectId],
    queryFn: () => api.getRequirementHistory(requirementId!, projectId!),
    enabled: !!requirementId && !!projectId,
  });
}
