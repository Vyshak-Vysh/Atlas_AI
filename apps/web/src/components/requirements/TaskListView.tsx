"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import { useSprints } from "@/hooks/useSprints";
import { useProjectMembers } from "@/hooks/useTeam";
import { requirementStatusDisplay, taskPriorityDisplay, taskStatusDisplay, TASK_STATUS_COLUMNS } from "@/lib/status";
import type { RequirementResponse } from "@/lib/types";
import { Avatar } from "@/components/ui/Avatar";
import { Badge, StatusBadge } from "@/components/ui/Badge";

// Simple heuristic — this app has no separate "% complete" field, so the
// progress bar derives from task_status the same way the ClickUp-style
// reference view implies it (DONE = full, in-flight states = half, not
// started/blocked = empty).
function progressForTaskStatus(taskStatus: string): number {
  if (taskStatus === "DONE") return 100;
  if (taskStatus === "IN_PROGRESS" || taskStatus === "IN_REVIEW") return 50;
  return 0;
}

export function TaskListView({
  requirements,
  projectId,
  onOpenTask,
}: {
  requirements: RequirementResponse[];
  projectId: string;
  onOpenTask: (id: string) => void;
}) {
  const { data: members } = useProjectMembers(projectId);
  const { data: sprints } = useSprints(projectId);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const assigneeName = (userId: string | null) =>
    members?.find((m) => m.user_id === userId)?.display_name ?? null;
  const sprintName = (sprintId: string | null) => sprints?.find((s) => s.id === sprintId)?.name ?? null;

  const grouped = TASK_STATUS_COLUMNS.map((column) => ({
    column,
    tasks: requirements.filter((r) => r.task_status === column.value),
  })).filter((group) => group.tasks.length > 0);

  return (
    <div>
      {grouped.map(({ column, tasks }) => {
        const isCollapsed = collapsed[column.value];
        return (
          <div key={column.value} className="task-list-section">
            <div
              className="task-list-section__header"
              onClick={() => setCollapsed((prev) => ({ ...prev, [column.value]: !prev[column.value] }))}
            >
              {isCollapsed ? <ChevronRight size={16} aria-hidden /> : <ChevronDown size={16} aria-hidden />}
              <StatusBadge status={taskStatusDisplay(column.value)} />
              <span className="task-list-section__count">{tasks.length}</span>
            </div>

            {!isCollapsed && (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Progress</th>
                      <th>Assignee</th>
                      <th>Due date</th>
                      <th>Priority</th>
                      <th>Verification status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((task) => {
                      const priority = taskPriorityDisplay(task.priority);
                      const progress = progressForTaskStatus(task.task_status);
                      const assignee = assigneeName(task.assignee_id);
                      const sprint = sprintName(task.sprint_id);
                      return (
                        <tr key={task.id} className="is-clickable" onClick={() => onOpenTask(task.id)}>
                          <td>
                            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                              <span style={{ fontFamily: "var(--font-family-mono)", fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                                {task.key}
                              </span>
                              <span>{task.title}</span>
                              {sprint && <Badge variant="discovery">{sprint}</Badge>}
                            </div>
                          </td>
                          <td>
                            <div className="task-progress">
                              <div className="task-progress__track">
                                <div className="task-progress__fill" style={{ width: `${progress}%` }} />
                              </div>
                              <span className="task-progress__label">{progress}%</span>
                            </div>
                          </td>
                          <td>
                            {assignee ? (
                              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                                <Avatar name={assignee} size={22} />
                                <span>{assignee}</span>
                              </div>
                            ) : (
                              <span style={{ color: "var(--text-secondary)" }}>Unassigned</span>
                            )}
                          </td>
                          <td>{task.due_date ?? <span style={{ color: "var(--text-secondary)" }}>—</span>}</td>
                          <td>
                            <Badge variant={priority.variant}>{priority.label}</Badge>
                          </td>
                          <td>
                            <StatusBadge status={requirementStatusDisplay(task.status)} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
