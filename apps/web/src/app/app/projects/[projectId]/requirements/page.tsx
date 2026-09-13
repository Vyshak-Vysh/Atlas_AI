"use client";

import { ClipboardList, Plus } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { useProjectOverview } from "@/hooks/useProjects";
import { useCreateRequirement, useRequirements } from "@/hooks/useRequirements";
import { ApiError } from "@/lib/api";
import { requirementStatusDisplay } from "@/lib/status";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
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

export default function RequirementsListPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("ALL");
  const { data: requirements, isLoading, error, refetch } = useRequirements(
    params.projectId,
    statusFilter === "ALL" ? undefined : statusFilter,
  );
  const { data: overview } = useProjectOverview(params.projectId);
  const [showCreate, setShowCreate] = useState(false);

  const phaseName = (phaseId: string | null) => overview?.phases.find((p) => p.id === phaseId)?.name ?? "—";

  return (
    <div>
      <PageHeader
        title="Requirements"
        description="Normalized project requirements and their current verification status."
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus size={16} aria-hidden /> Add requirement
          </Button>
        }
      />

      <div style={{ marginBottom: "var(--space-5)" }}>
        <select className="select" style={{ maxWidth: "16rem" }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="ALL">All statuses</option>
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
          title="No requirements captured yet"
          description="Add requirements manually, or they'll appear as investigations map evidence to project scope."
          actions={<Button size="small" onClick={() => setShowCreate(true)}>Add requirement</Button>}
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Key</th>
                <th>Title</th>
                <th>Phase</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {requirements.map((req) => (
                <tr key={req.id} className="is-clickable" onClick={() => router.push(`/app/projects/${params.projectId}/requirements/${req.id}`)}>
                  <td style={{ fontFamily: "var(--font-family-mono)", fontSize: "var(--font-size-xs)" }}>{req.key}</td>
                  <td>{req.title}</td>
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
  const [key, setKey] = useState("");
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("CAPTURED");
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
        phase_id: phaseId || undefined,
        description: description.trim() || undefined,
      });
      setKey("");
      setTitle("");
      setDescription("");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Failed to create requirement.");
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Add requirement"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={createRequirement.isPending} disabled={!key.trim() || !title.trim()}>
            Add requirement
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
        <Field label="Status" htmlFor="req-status">
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
