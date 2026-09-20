"use client";

import { useQueries } from "@tanstack/react-query";
import { CalendarClock, ClipboardCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/lib/auth-context";
import { useProjects } from "@/hooks/useProjects";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { taskPriorityDisplay, taskStatusDisplay, TASK_PRIORITIES, TASK_STATUS_COLUMNS } from "@/lib/status";
import type { ProjectResponse, RequirementResponse } from "@/lib/types";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { SkeletonTable } from "@/components/ui/Skeleton";

/**
 * My Work — every task assigned to YOU, across every project you have
 * access to, in one place. This used to be a single-project board
 * switcher (redundant with each project's own "Tasks" tab and the
 * Sidebar's project tree); the one thing nothing else in the app could
 * answer was "what's actually on my plate right now across every client,"
 * so that's what this page does instead. Fans out the same per-project
 * requirements endpoint every project's own Tasks tab already calls,
 * filtered to the current user as assignee, one call per project — the
 * same reuse pattern as the Space-level Findings/Approvals rollups.
 */
export default function MyWorkPage() {
  const router = useRouter();
  const { session } = useAuth();
  const { data: projects, isLoading: projectsLoading, error: projectsError, refetch } = useProjects();
  const [taskStatusFilter, setTaskStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [page, setPage] = useState(1);

  const results = useQueries({
    queries: (projects ?? []).map((project) => ({
      queryKey: ["my-tasks", project.id, session?.userId, taskStatusFilter, priorityFilter],
      queryFn: () =>
        api.listRequirements(project.id, {
          assigneeId: session!.userId,
          taskStatus: taskStatusFilter === "ALL" ? undefined : taskStatusFilter,
          priority: priorityFilter === "ALL" ? undefined : priorityFilter,
        }),
      enabled: !!session,
    })),
  });

  const tasksLoading = results.some((r) => r.isLoading);
  const tasksError = results.find((r) => r.error)?.error;

  const items: { project: ProjectResponse; task: RequirementResponse }[] = (projects ?? []).flatMap(
    (project, i) => (results[i]?.data ?? []).map((task) => ({ project, task })),
  );
  items.sort((a, b) => {
    if (a.task.due_date && b.task.due_date) return a.task.due_date.localeCompare(b.task.due_date);
    if (a.task.due_date) return -1;
    if (b.task.due_date) return 1;
    return b.task.created_at.localeCompare(a.task.created_at);
  });
  const { pageRows, page: currentPage, pageCount } = usePagination(items, page, setPage);

  const loading = projectsLoading || (!!projects && projects.length > 0 && tasksLoading);

  return (
    <div>
      <PageHeader title="My Work" description="Every task assigned to you, across every project you have access to." />

      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
        <select
          className="select"
          style={{ maxWidth: "14rem" }}
          value={taskStatusFilter}
          onChange={(e) => {
            setTaskStatusFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="ALL">All task statuses</option>
          {TASK_STATUS_COLUMNS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <select
          className="select"
          style={{ maxWidth: "12rem" }}
          value={priorityFilter}
          onChange={(e) => {
            setPriorityFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="ALL">All priorities</option>
          {TASK_PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {taskPriorityDisplay(p).label}
            </option>
          ))}
        </select>
      </div>

      {projectsError ? (
        <ErrorState error={projectsError} onRetry={() => refetch()} />
      ) : tasksError ? (
        <ErrorState error={tasksError} onRetry={() => results.forEach((r) => r.refetch())} />
      ) : loading ? (
        <SkeletonTable rows={6} />
      ) : !projects || projects.length === 0 ? (
        <EmptyState icon={ClipboardCheck} title="No projects yet" description="Once you're on a project, tasks assigned to you will show up here." />
      ) : items.length === 0 ? (
        <EmptyState icon={ClipboardCheck} title="Nothing assigned to you right now" description="Tasks assigned to you across any project will show up here." />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Project</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Due</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map(({ project, task }) => (
                <tr
                  key={task.id}
                  className="is-clickable"
                  onClick={() => router.push(`/app/projects/${project.id}/requirements/${task.id}`)}
                >
                  <td>
                    <span style={{ fontFamily: "var(--font-family-mono)", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)", marginRight: "var(--space-2)" }}>
                      {task.key}
                    </span>
                    {task.title}
                  </td>
                  <td>{project.name}</td>
                  <td>
                    <StatusBadge status={taskStatusDisplay(task.task_status)} />
                  </td>
                  <td>
                    <Badge variant={taskPriorityDisplay(task.priority).variant}>{taskPriorityDisplay(task.priority).label}</Badge>
                  </td>
                  <td>
                    {task.due_date ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}>
                        <CalendarClock size={13} aria-hidden style={{ color: "var(--text-tertiary)" }} />
                        {formatDate(task.due_date)}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={currentPage} pageCount={pageCount} onPageChange={setPage} totalItems={items.length} pageSize={25} />
        </div>
      )}
    </div>
  );
}
