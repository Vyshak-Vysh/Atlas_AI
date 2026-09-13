"use client";

import { useQueries } from "@tanstack/react-query";
import { useMemo } from "react";

import { api } from "@/lib/api";
import type { ActionResponse, ProjectResponse } from "@/lib/types";
import { useProjects } from "./useProjects";

export interface ProjectAction {
  project: ProjectResponse;
  action: ActionResponse;
}

/** Same cross-project composition pattern as useFindingsAcrossProjects —
 * there is no cross-project actions endpoint, so this fans out the
 * real per-project list (used by the project Approvals tab) rather than
 * fabricating anything. */
export function useActionsAcrossProjects(status?: string) {
  const { data: projects, isLoading: projectsLoading } = useProjects();

  const results = useQueries({
    queries: (projects ?? []).map((project) => ({
      queryKey: ["actions", project.id, status],
      queryFn: () => api.listActions(project.id, status),
      enabled: !!projects,
      refetchInterval: 20_000,
    })),
  });

  const all = useMemo<ProjectAction[]>(() => {
    if (!projects) return [];
    const out: ProjectAction[] = [];
    results.forEach((result, i) => {
      const project = projects[i];
      if (!project || !result.data) return;
      for (const action of result.data) out.push({ project, action });
    });
    return out.sort((a, b) => new Date(b.action.created_at).getTime() - new Date(a.action.created_at).getTime());
  }, [results, projects]);

  return { all, isLoading: projectsLoading || results.some((r) => r.isLoading) };
}
