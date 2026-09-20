"use client";

import { History, MessageSquare, Trash2 } from "lucide-react";
import { useState } from "react";

import { useProjectOverview } from "@/hooks/useProjects";
import { useCurrentRole } from "@/hooks/useCurrentWorkspace";
import { useDeleteRequirement, useRequirement, useUpdateRequirement } from "@/hooks/useRequirements";
import { useSprints } from "@/hooks/useSprints";
import { ApiError } from "@/lib/api";
import { roleHasPermission } from "@/lib/permissions";
import { requirementStatusDisplay, taskPriorityDisplay, taskStatusDisplay, TASK_PRIORITIES, TASK_STATUS_COLUMNS } from "@/lib/status";
import { formatDateTime, formatPercent } from "@/lib/format";
import { useToast } from "@/lib/toast";
import { AssigneePicker } from "./AssigneePicker";
import { CommentThread } from "./CommentThread";
import { TaskHistoryTimeline } from "./TaskHistoryTimeline";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ErrorState } from "@/components/ui/ErrorState";
import { Select, Textarea } from "@/components/ui/Field";
import { SkeletonCard } from "@/components/ui/Skeleton";

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

type Tab = "details" | "comments" | "history";

export function TaskDetailContent({
  requirementId,
  projectId,
  onDeleted,
}: {
  requirementId: string;
  projectId: string;
  onDeleted?: () => void;
}) {
  const role = useCurrentRole();
  const { data, isLoading, error, refetch } = useRequirement(requirementId, projectId);
  const { data: overview } = useProjectOverview(projectId);
  const { data: sprints } = useSprints(projectId);
  const updateRequirement = useUpdateRequirement(projectId);
  const deleteRequirement = useDeleteRequirement(projectId);
  const [tab, setTab] = useState<Tab>("details");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [descriptionDraft, setDescriptionDraft] = useState<string | null>(null);
  const { toast } = useToast();

  const canEdit = roleHasPermission(role, "EDIT_TASK");
  const canAssign = roleHasPermission(role, "ASSIGN_TASK");
  const canDelete = roleHasPermission(role, "DELETE_TASK");

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (isLoading || !data) return <SkeletonCard />;

  const { requirement, evidence_links, delivery_records } = data;
  const phaseName = overview?.phases.find((p) => p.id === requirement.phase_id)?.name ?? "No phase";

  async function handleDelete() {
    try {
      await deleteRequirement.mutateAsync(requirementId);
      onDeleted?.();
    } catch (err) {
      toast({
        variant: "danger",
        title: "Couldn't delete task",
        description:
          err instanceof ApiError && err.status === 409
            ? String(err.detail ?? "This task has linked evidence — change its task status instead.")
            : "Something went wrong. Please try again.",
      });
      throw err;
    }
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)", marginBottom: "var(--space-4)" }}>
        <div>
          <p style={{ margin: 0, fontFamily: "var(--font-family-mono)", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
            {requirement.key} · {phaseName}
          </p>
          <h1 style={{ margin: "var(--space-1) 0 0", fontSize: "var(--font-size-xl)", fontWeight: "var(--font-weight-semibold)" }}>
            {requirement.title}
          </h1>
        </div>
        {canDelete && (
          <Button variant="danger" size="small" onClick={() => setConfirmDelete(true)}>
            <Trash2 size={14} aria-hidden /> Delete
          </Button>
        )}
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
        <div>
          <p style={{ margin: "0 0 var(--space-1)", fontSize: "var(--font-size-2xs)", color: "var(--text-tertiary)" }}>Task status</p>
          {canEdit ? (
            <Select
              value={requirement.task_status}
              onChange={(e) => updateRequirement.mutate({ requirementId, task_status: e.target.value })}
              style={{ maxWidth: "10rem" }}
            >
              {TASK_STATUS_COLUMNS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          ) : (
            <StatusBadge status={taskStatusDisplay(requirement.task_status)} />
          )}
        </div>

        <div>
          <p style={{ margin: "0 0 var(--space-1)", fontSize: "var(--font-size-2xs)", color: "var(--text-tertiary)" }}>Priority</p>
          {canEdit ? (
            <Select
              value={requirement.priority}
              onChange={(e) => updateRequirement.mutate({ requirementId, priority: e.target.value })}
              style={{ maxWidth: "8rem" }}
            >
              {TASK_PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {taskPriorityDisplay(p).label}
                </option>
              ))}
            </Select>
          ) : (
            <Badge variant={taskPriorityDisplay(requirement.priority).variant}>{taskPriorityDisplay(requirement.priority).label}</Badge>
          )}
        </div>

        <div>
          <p style={{ margin: "0 0 var(--space-1)", fontSize: "var(--font-size-2xs)", color: "var(--text-tertiary)" }}>Assignee</p>
          <AssigneePicker
            projectId={projectId}
            assigneeId={requirement.assignee_id}
            disabled={!canAssign}
            onChange={(userId) => updateRequirement.mutate({ requirementId, assignee_id: userId })}
          />
        </div>

        <div>
          <p style={{ margin: "0 0 var(--space-1)", fontSize: "var(--font-size-2xs)", color: "var(--text-tertiary)" }}>Sprint</p>
          {canEdit ? (
            <Select
              value={requirement.sprint_id ?? ""}
              onChange={(e) => updateRequirement.mutate({ requirementId, sprint_id: e.target.value || null })}
              style={{ maxWidth: "10rem" }}
            >
              <option value="">No sprint</option>
              {(sprints ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          ) : (
            <span style={{ fontSize: "var(--font-size-sm)" }}>
              {sprints?.find((s) => s.id === requirement.sprint_id)?.name ?? "No sprint"}
            </span>
          )}
        </div>

        <div>
          <p style={{ margin: "0 0 var(--space-1)", fontSize: "var(--font-size-2xs)", color: "var(--text-tertiary)" }}>Verification status</p>
          {canEdit ? (
            <Select
              value={requirement.status}
              onChange={(e) => updateRequirement.mutate({ requirementId, status: e.target.value })}
              style={{ maxWidth: "12rem" }}
            >
              {REQUIREMENT_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {requirementStatusDisplay(s).label}
                </option>
              ))}
            </Select>
          ) : (
            <StatusBadge status={requirementStatusDisplay(requirement.status)} />
          )}
        </div>
      </div>

      <div className="tabs" role="tablist">
        <button type="button" className="tab" aria-current={tab === "details" ? "page" : undefined} onClick={() => setTab("details")}>
          Details
        </button>
        <button type="button" className="tab" aria-current={tab === "comments" ? "page" : undefined} onClick={() => setTab("comments")}>
          <MessageSquare size={14} aria-hidden /> Comments
        </button>
        <button type="button" className="tab" aria-current={tab === "history" ? "page" : undefined} onClick={() => setTab("history")}>
          <History size={14} aria-hidden /> History
        </button>
      </div>

      {tab === "details" && (
        <div style={{ display: "grid", gap: "var(--space-5)" }}>
          <Card>
            <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Description</h2>} />
            <CardBody>
              {canEdit ? (
                <Textarea
                  rows={4}
                  value={descriptionDraft ?? requirement.description ?? ""}
                  onChange={(e) => setDescriptionDraft(e.target.value)}
                  onBlur={() => {
                    if (descriptionDraft !== null && descriptionDraft !== (requirement.description ?? "")) {
                      updateRequirement.mutate({ requirementId, description: descriptionDraft || null });
                    }
                  }}
                />
              ) : requirement.description ? (
                <p style={{ margin: 0, fontSize: "var(--font-size-sm)", lineHeight: "var(--line-height-relaxed)" }}>{requirement.description}</p>
              ) : (
                <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>No description yet.</p>
              )}
            </CardBody>
          </Card>

          {requirement.acceptance_criteria.length > 0 && (
            <Card>
              <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Acceptance criteria</h2>} />
              <CardBody>
                <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "var(--font-size-sm)" }}>
                  {requirement.acceptance_criteria.map((c, i) => (
                    <li key={i}>{String(c)}</li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          )}

          <Card>
            <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Supporting evidence links ({evidence_links.length})</h2>} />
            <CardBody>
              {evidence_links.length === 0 ? (
                <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>
                  No evidence has been explicitly linked to this task yet.
                </p>
              ) : (
                <div style={{ display: "grid", gap: "var(--space-2)" }}>
                  {evidence_links.map((link, i) => (
                    <div key={i} className="card" style={{ padding: "var(--space-3)", display: "flex", justifyContent: "space-between" }}>
                      <span className="badge badge--neutral">{link.relation_type}</span>
                      {link.confidence !== null && <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>{formatPercent(link.confidence)} confidence</span>}
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Delivery records ({delivery_records.length})</h2>} />
            <CardBody>
              {delivery_records.length === 0 ? (
                <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>No delivery records yet.</p>
              ) : (
                <div style={{ display: "grid", gap: "var(--space-2)" }}>
                  {delivery_records.map((record) => (
                    <div key={record.id} className="card" style={{ padding: "var(--space-3)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span className="badge badge--info">{record.status.replaceAll("_", " ")}</span>
                        {record.verified_at && <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>{formatDateTime(record.verified_at)}</span>}
                      </div>
                      {record.evidence_summary && <p style={{ margin: "var(--space-2) 0 0", fontSize: "var(--font-size-sm)" }}>{record.evidence_summary}</p>}
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {tab === "comments" && <CommentThread requirementId={requirementId} projectId={projectId} />}
      {tab === "history" && <TaskHistoryTimeline requirementId={requirementId} projectId={projectId} />}

      <ConfirmDialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
        title="Delete this task?"
        description="This permanently removes the task. Tasks with linked evidence or delivery records can't be deleted — change their task status instead."
        confirmLabel="Delete task"
      />
    </div>
  );
}
