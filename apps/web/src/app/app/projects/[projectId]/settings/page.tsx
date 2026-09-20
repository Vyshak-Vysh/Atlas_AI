"use client";

import { Plus, Trash2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { useCreatePhase, useDeleteProject, useProjectOverview, useUpdateProject } from "@/hooks/useProjects";
import { useCurrentRole } from "@/hooks/useCurrentWorkspace";
import { useSpaces } from "@/hooks/useSpaces";
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
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
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

      <ProjectDetailsCard
        projectId={params.projectId}
        name={overview.project.name}
        clientName={overview.project.client_name}
        status={overview.project.status}
        spaceId={overview.project.space_id}
        canManage={canManage}
      />
      <PhasesCard projectId={params.projectId} phases={overview.phases} canManage={canManage} />
      <ProjectTeamCard projectId={params.projectId} canManage={canManage} />
      {canManage && <DangerZoneCard projectId={params.projectId} projectName={overview.project.name} />}
    </div>
  );
}

function DangerZoneCard({ projectId, projectName }: { projectId: string; projectName: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const deleteProject = useDeleteProject();
  const [showDelete, setShowDelete] = useState(false);

  return (
    <Card style={{ borderColor: "var(--border-danger)" }}>
      <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)", color: "var(--color-danger-700)" }}>Danger zone</h2>} />
      <CardBody>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-4)" }}>
          <div>
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)", fontWeight: "var(--font-weight-medium)" }}>Delete this project</p>
            <p style={{ margin: "var(--space-1) 0 0", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
              Permanently deletes every task, finding, investigation, action, and connector for this project. This can&rsquo;t be undone.
            </p>
          </div>
          <Button variant="danger" size="small" onClick={() => setShowDelete(true)} style={{ flexShrink: 0 }}>
            <Trash2 size={14} aria-hidden /> Delete project
          </Button>
        </div>
      </CardBody>

      <ConfirmDialog
        open={showDelete}
        onClose={() => setShowDelete(false)}
        title="Delete this project?"
        description={`This permanently deletes "${projectName}" and every task, finding, investigation, action, and connector inside it. Evidence already synced from its connectors stays available to any other project that also has it in scope. This can't be undone.`}
        confirmLabel="Delete project"
        onConfirm={async () => {
          try {
            await deleteProject.mutateAsync(projectId);
            toast({ title: "Project deleted", variant: "success" });
            router.push("/app/projects");
          } catch (err) {
            toast({ title: "Couldn't delete project", description: err instanceof ApiError ? String(err.detail) : undefined, variant: "danger" });
          }
        }}
      />
    </Card>
  );
}

function ProjectDetailsCard({
  projectId,
  name,
  clientName,
  status,
  spaceId,
  canManage,
}: {
  projectId: string;
  name: string;
  clientName: string | null;
  status: string;
  spaceId: string | null;
  canManage: boolean;
}) {
  const update = useUpdateProject(projectId);
  const { data: spaces } = useSpaces();
  const { toast } = useToast();
  const [localName, setLocalName] = useState(name);
  const [localClient, setLocalClient] = useState(clientName ?? "");
  const [localStatus, setLocalStatus] = useState(status);
  const [localSpaceId, setLocalSpaceId] = useState(spaceId ?? "");

  async function handleSave() {
    try {
      await update.mutateAsync({
        name: localName,
        client_name: localClient,
        status: localStatus,
        // The API has no way to *clear* a project's space back to "none" —
        // only to set/change it — so an empty selection is simply left out
        // of the request rather than sent as an empty string.
        ...(localSpaceId ? { space_id: localSpaceId } : {}),
      });
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
          <Field
            label="Space"
            htmlFor="pspace"
            hint={localSpaceId ? "Moving a project changes where it appears in the sidebar tree." : "This project isn't in a space yet."}
          >
            <Select id="pspace" value={localSpaceId} onChange={(e) => setLocalSpaceId(e.target.value)} disabled={!canManage}>
              <option value="" disabled={!!localSpaceId}>
                No space
              </option>
              {(spaces ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
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

