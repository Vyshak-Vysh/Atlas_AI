"use client";

import { Plus } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { useCreatePhase, useProjectOverview, useUpdateProject } from "@/hooks/useProjects";
import { useCurrentRole } from "@/hooks/useCurrentWorkspace";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { roleHasPermission } from "@/lib/permissions";
import { phaseStatusDisplay } from "@/lib/status";
import { useToast } from "@/lib/toast";
import { ProjectTeamCard } from "@/components/team/ProjectTeamCard";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Field, Input, Select } from "@/components/ui/Field";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";

export default function ProjectSettingsPage() {
  const params = useParams<{ projectId: string }>();
  const { data: overview, isLoading, error, refetch } = useProjectOverview(params.projectId);
  const role = useCurrentRole();
  const canManage = roleHasPermission(role, "MANAGE_PROJECT_MEMBERS");

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (isLoading || !overview) return <SkeletonCard />;

  return (
    <div style={{ display: "grid", gap: "var(--space-5)", maxWidth: "44rem" }}>
      <PageHeader title="Project settings" description="Manage this project's details, phases, and team." />

      <ProjectDetailsCard projectId={params.projectId} name={overview.project.name} clientName={overview.project.client_name} status={overview.project.status} canManage={canManage} />
      <PhasesCard projectId={params.projectId} phases={overview.phases} canManage={canManage} />
      <ProjectTeamCard projectId={params.projectId} canManage={canManage} />
    </div>
  );
}

function ProjectDetailsCard({
  projectId,
  name,
  clientName,
  status,
  canManage,
}: {
  projectId: string;
  name: string;
  clientName: string | null;
  status: string;
  canManage: boolean;
}) {
  const update = useUpdateProject(projectId);
  const { toast } = useToast();
  const [localName, setLocalName] = useState(name);
  const [localClient, setLocalClient] = useState(clientName ?? "");
  const [localStatus, setLocalStatus] = useState(status);

  async function handleSave() {
    try {
      await update.mutateAsync({ name: localName, client_name: localClient, status: localStatus });
      toast({ title: "Project updated", variant: "success" });
    } catch (err) {
      toast({ title: "Couldn't save", description: err instanceof ApiError ? String(err.detail) : undefined, variant: "danger" });
    }
  }

  return (
    <Card>
      <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Details</h2>} />
      <CardBody>
        <div style={{ display: "grid", gap: "var(--space-4)" }}>
          <Field label="Project name" htmlFor="pname">
            <Input id="pname" value={localName} onChange={(e) => setLocalName(e.target.value)} disabled={!canManage} />
          </Field>
          <Field label="Client name" htmlFor="pclient">
            <Input id="pclient" value={localClient} onChange={(e) => setLocalClient(e.target.value)} disabled={!canManage} />
          </Field>
          <Field label="Status" htmlFor="pstatus">
            <Select id="pstatus" value={localStatus} onChange={(e) => setLocalStatus(e.target.value)} disabled={!canManage}>
              {["ACTIVE", "ON_HOLD", "COMPLETED", "ARCHIVED"].map((s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ))}
            </Select>
          </Field>
          {canManage && (
            <Button onClick={handleSave} loading={update.isPending} style={{ justifySelf: "start" }}>
              Save changes
            </Button>
          )}
        </div>
      </CardBody>
    </Card>
  );
}

function PhasesCard({
  projectId,
  phases,
  canManage,
}: {
  projectId: string;
  phases: { id: string; name: string; phase_number: number; status: string; start_date: string | null; end_date: string | null }[];
  canManage: boolean;
}) {
  const createPhase = useCreatePhase(projectId);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [phaseNumber, setPhaseNumber] = useState(phases.length + 1);

  return (
    <Card>
      <CardHeader
        title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Phases</h2>}
        actions={
          canManage && (
            <Button variant="secondary" size="small" onClick={() => setShowForm((s) => !s)}>
              <Plus size={14} aria-hidden /> Add phase
            </Button>
          )
        }
      />
      <CardBody>
        {phases.length === 0 ? (
          <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>No phases yet.</p>
        ) : (
          <div style={{ display: "grid", gap: "var(--space-2)" }}>
            {phases
              .slice()
              .sort((a, b) => a.phase_number - b.phase_number)
              .map((phase) => (
                <div key={phase.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-2) 0", borderBottom: "1px solid var(--border-subtle)" }}>
                  <span style={{ fontSize: "var(--font-size-sm)" }}>
                    Phase {phase.phase_number}: {phase.name}
                    {phase.start_date && ` · ${formatDate(phase.start_date)}`}
                  </span>
                  <StatusBadge status={phaseStatusDisplay(phase.status)} />
                </div>
              ))}
          </div>
        )}

        {showForm && (
          <form
            style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-4)" }}
            onSubmit={async (e) => {
              e.preventDefault();
              await createPhase.mutateAsync({ name, phase_number: phaseNumber });
              setName("");
              setShowForm(false);
            }}
          >
            <Input type="number" min={1} value={phaseNumber} onChange={(e) => setPhaseNumber(Number(e.target.value))} style={{ maxWidth: "5rem" }} />
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Phase name" required />
            <Button type="submit" size="small" loading={createPhase.isPending}>
              Add
            </Button>
          </form>
        )}
      </CardBody>
    </Card>
  );
}

