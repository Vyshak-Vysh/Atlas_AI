"use client";

import { useQueries } from "@tanstack/react-query";
import { useMemo } from "react";

import { api } from "@/lib/api";
import type { ActionResponse, ProjectResponse } from "@/lib/types";
import { useProjects } from "./useProjects";

export interface NotificationItem {
  project: ProjectResponse;
  action: ActionResponse;
}

/** Cross-project pending-approval notifications, polled every 20s. There is
 * no dedicated notifications endpoint in this deployment — this composes
 * the real per-project actions list (already used by the Approvals queue)
 * across every project the caller belongs to, so what's shown here is
 * always live approval-queue data, never a fabricated feed. */
export function usePendingApprovalNotifications() {
  const { data: projects } = useProjects();

  const results = useQueries({
    queries: (projects ?? []).map((project) => ({
      queryKey: ["actions", project.id, "WAITING_APPROVAL"],
      queryFn: () => api.listActions(project.id, "WAITING_APPROVAL"),
      enabled: !!projects,
      refetchInterval: 20_000,
      meta: { project },
    })),
  });

  const items = useMemo<NotificationItem[]>(() => {
    if (!projects) return [];
    const out: NotificationItem[] = [];
    results.forEach((result, index) => {
      const project = projects[index];
      if (!project || !result.data) return;
      for (const action of result.data) out.push({ project, action });
    });
    return out.sort((a, b) => new Date(b.action.created_at).getTime() - new Date(a.action.created_at).getTime());
  }, [results, projects]);

  const isLoading = results.some((r) => r.isLoading);

  return { items, isLoading };
}
