"use client";

import { ClipboardList, LayoutGrid, List, Plus } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { useCurrentRole } from "@/hooks/useCurrentWorkspace";
import { useProjectOverview } from "@/hooks/useProjects";
import { useProjectMembers } from "@/hooks/useTeam";
import { useCreateRequirement, useRequirements } from "@/hooks/useRequirements";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { roleHasPermission } from "@/lib/permissions";
import { requirementStatusDisplay, taskPriorityDisplay, taskStatusDisplay, TASK_PRIORITIES, TASK_STATUS_COLUMNS } from "@/lib/status";
import { KanbanBoard } from "@/components/requirements/KanbanBoard";
import { TaskDetailDrawer } from "@/components/requirements/TaskDetailDrawer";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge, Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Field, Input, Select, Textarea } from "@/components/ui/Field";
import { SkeletonTable } from "@/components/ui/Skeleton";

const REQUIREMENT_STATUSES = [
  "PROPOSED",
  "CAPTURED",
  "VALIDATED",
  "APPROVED",
  "IN_PROGRESS",
  "PARTIALLY_DELIVERED",
  "DELIVERED_VERIFIED",
  "SUPERSEDED",
  "AMBIGUOUS",
  "CONFLICTING",
  "NOT_VERIFIED",
  "CANCELLED",
  "REJECTED",
];

type View = "list" | "board";

export default function RequirementsListPage() {
  const params = useParams<{ projectId: string }>();
  const role = useCurrentRole();
  const [view, setView] = useState<View>("board");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [taskStatusFilter, setTaskStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [openTaskId, setOpenTaskId] = useState<string | null>(null);
  const { data: requirements, isLoading, error, refetch } = useRequirements(params.projectId, {
    status: statusFilter === "ALL" ? undefined : statusFilter,
    taskStatus: taskStatusFilter === "ALL" ? undefined : taskStatusFilter,
    priority: priorityFilter === "ALL" ? undefined : priorityFilter,
  });
  const { data: overview } = useProjectOverview(params.projectId);
  const { data: members } = useProjectMembers(params.projectId);
  const [showCreate, setShowCreate] = useState(false);

  const canCreate = roleHasPermission(role, "CREATE_TASK");
  const canEdit = roleHasPermission(role, "EDIT_TASK");

  const phaseName = (phaseId: string | null) => overview?.phases.find((p) => p.id === phaseId)?.name ?? "—";
  const assigneeName = (userId: string | null) => members?.find((m) => m.user_id === userId)?.display_name ?? "Unassigned";

  return (
    <div>
      <PageHeader
        title="Tasks"
        description="Plan, assign, and track delivery work for this project."
        actions={
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <div style={{ display: "flex", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
              <button
                type="button"
                className={cn("button", "button--small", view === "board" ? "button--secondary" : "button--ghost")}
                style={{ borderRadius: 0 }}
                onClick={() => setView("board")}
              >
                <LayoutGrid size={14} aria-hidden /> Board
              </button>
              <button
                type="button"
                className={cn("button", "button--small", view === "list" ? "button--secondary" : "button--ghost")}
                style={{ borderRadius: 0 }}
                onClick={() => setView("list")}
              >
                <List size={14} aria-hidden /> List
              </button>
            </div>
            {canCreate && (
              <Button onClick={() => setShowCreate(true)}>
                <Plus size={16} aria-hidden /> Add task
              </Button>
            )}
          </div>
        }
      />

      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
        <select className="select" style={{ maxWidth: "14rem" }} value={taskStatusFilter} onChange={(e) => setTaskStatusFilter(e.target.value)}>
          <option value="ALL">All task statuses</option>
          {TASK_STATUS_COLUMNS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <select className="select" style={{ maxWidth: "12rem" }} value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
          <option value="ALL">All priorities</option>
          {TASK_PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {taskPriorityDisplay(p).label}
            </option>
          ))}
        </select>
        <select className="select" style={{ maxWidth: "16rem" }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="ALL">All verification statuses</option>
          {REQUIREMENT_STATUSES.map((s) => (
            <option key={s} value={s}>
              {requirementStatusDisplay(s).label}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonTable rows={5} />
      ) : !requirements || requirements.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No tasks yet"
          description="Add tasks manually, or they'll appear as investigations map evidence to project scope."
          actions={canCreate ? <Button size="small" onClick={() => setShowCreate(true)}>Add task</Button> : undefined}
        />
      ) : view === "board" ? (
        <KanbanBoard
          requirements={requirements}
          projectId={params.projectId}
          canDrag={canEdit}
          onOpenTask={setOpenTaskId}
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Key</th>
                <th>Title</th>
                <th>Task status</th>
                <th>Priority</th>
                <th>Assignee</th>
                <th>Phase</th>
                <th>Verification status</th>
              </tr>
            </thead>
            <tbody>
              {requirements.map((req) => (
                <tr key={req.id} className="is-clickable" onClick={() => setOpenTaskId(req.id)}>
                  <td style={{ fontFamily: "var(--font-family-mono)", fontSize: "var(--font-size-xs)" }}>{req.key}</td>
                  <td>{req.title}</td>
                  <td>
                    <StatusBadge status={taskStatusDisplay(req.task_status)} />
                  </td>
                  <td>
                    <Badge variant={taskPriorityDisplay(req.priority).variant}>{taskPriorityDisplay(req.priority).label}</Badge>
                  </td>
                  <td>{assigneeName(req.assignee_id)}</td>
                  <td>{phaseName(req.phase_id)}</td>
                  <td>
                    <StatusBadge status={requirementStatusDisplay(req.status)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CreateRequirementDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        projectId={params.projectId}
        phases={overview?.phases ?? []}
      />

      <TaskDetailDrawer
        requirementId={openTaskId}
        projectId={params.projectId}
        onClose={() => setOpenTaskId(null)}
      />
    </div>
  );
}

function CreateRequirementDialog({
  open,
  onClose,
  projectId,
  phases,
}: {
  open: boolean;
  onClose: () => void;
  projectId: string;
  phases: { id: string; name: string }[];
}) {
  const createRequirement = useCreateRequirement(projectId);
  const { data: members } = useProjectMembers(projectId);
  const [key, setKey] = useState("");
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("CAPTURED");
  const [taskStatus, setTaskStatus] = useState("TO_DO");
  const [priority, setPriority] = useState("NORMAL");
  const [assigneeId, setAssigneeId] = useState("");
  const [phaseId, setPhaseId] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setError(null);
    try {
      await createRequirement.mutateAsync({
        key: key.trim(),
        title: title.trim(),
        status,
        task_status: taskStatus,
        priority,
        assignee_id: assigneeId || undefined,
        phase_id: phaseId || undefined,
        description: description.trim() || undefined,
      });
      setKey("");
      setTitle("");
      setDescription("");
      setAssigneeId("");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Failed to create task.");
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Add task"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={createRequirement.isPending} disabled={!key.trim() || !title.trim()}>
            Add task
          </Button>
        </>
      }
    >
      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        {error && (
          <div className="error-state">
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{error}</p>
          </div>
        )}
        <Field label="Key" htmlFor="req-key" hint="Short unique identifier, e.g. REQ-014.">
          <Input id="req-key" value={key} onChange={(e) => setKey(e.target.value)} />
        </Field>
        <Field label="Title" htmlFor="req-title">
          <Input id="req-title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
          <Field label="Task status" htmlFor="req-task-status">
            <Select id="req-task-status" value={taskStatus} onChange={(e) => setTaskStatus(e.target.value)}>
              {TASK_STATUS_COLUMNS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Priority" htmlFor="req-priority">
            <Select id="req-priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
              {TASK_PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {taskPriorityDisplay(p).label}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Assignee" htmlFor="req-assignee">
          <Select id="req-assignee" value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
            <option value="">Unassigned</option>
            {(members ?? []).map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.display_name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Phase" htmlFor="req-phase">
          <Select id="req-phase" value={phaseId} onChange={(e) => setPhaseId(e.target.value)}>
            <option value="">No phase</option>
            {phases.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Verification status" htmlFor="req-status" hint="Evidence-backed scope/delivery status — separate from task status above.">
          <Select id="req-status" value={status} onChange={(e) => setStatus(e.target.value)}>
            {REQUIREMENT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {requirementStatusDisplay(s).label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Description" htmlFor="req-description">
          <Textarea id="req-description" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
      </div>
    </Dialog>
  );
}
