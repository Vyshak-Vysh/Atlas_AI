"use client";

import { useQueries } from "@tanstack/react-query";
import { useMemo } from "react";

import { api } from "@/lib/api";
import type { FindingResponse, ProjectResponse } from "@/lib/types";
import { useProjects } from "./useProjects";

export interface ProjectFindings {
  project: ProjectResponse;
  findings: FindingResponse[];
}

/** Aggregates findings across every project the caller belongs to. There is
 * no cross-project findings endpoint, so this composes the real per-project
 * list (same one the project Findings tab uses) rather than presenting any
 * placeholder data. Fine for the number of projects a single workspace
 * realistically has open at once; would need a dedicated backend endpoint
 * to stay cheap at very large project counts. */
export function useFindingsAcrossProjects() {
  const { data: projects, isLoading: projectsLoading } = useProjects();

  const results = useQueries({
    queries: (projects ?? []).map((project) => ({
      queryKey: ["findings", project.id, undefined],
      queryFn: () => api.listFindings(project.id),
      enabled: !!projects,
      refetchInterval: 30_000,
    })),
  });

  const byProject = useMemo<ProjectFindings[]>(() => {
    if (!projects) return [];
    return projects.map((project, i) => ({ project, findings: results[i]?.data ?? [] }));
  }, [projects, results]);

  const all = useMemo(() => byProject.flatMap((p) => p.findings.map((f) => ({ project: p.project, finding: f }))), [
    byProject,
  ]);

  return {
    byProject,
    all,
    isLoading: projectsLoading || results.some((r) => r.isLoading),
  };
}
