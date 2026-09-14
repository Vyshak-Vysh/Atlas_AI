"use client";

import { Boxes, ClipboardList, Users } from "lucide-react";
import { useEffect, useState } from "react";

import { useCurrentRole } from "@/hooks/useCurrentWorkspace";
import { useProjects } from "@/hooks/useProjects";
import { roleHasPermission } from "@/lib/permissions";
import { ProjectTasksView } from "@/components/requirements/ProjectTasksView";
import { ProjectTeamCard } from "@/components/team/ProjectTeamCard";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Select } from "@/components/ui/Field";
import { SkeletonTable } from "@/components/ui/Skeleton";

type Tab = "board" | "team";

/**
 * Project Space — a cross-project hub for day-to-day delivery work: pick a
 * project, then manage its task board (assignment, priority, status,
 * collaboration) and its team roster from one place, without having to
 * first drill into that project's own nav. Complements, rather than
 * replaces, the per-project "Tasks" item under each project's own sidebar.
 */
export default function ProjectSpacePage() {
  const role = useCurrentRole();
  const { data: projects, isLoading, error, refetch } = useProjects();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("board");

  useEffect(() => {
    if (!projectId && projects && projects.length > 0) {
      setProjectId(projects[0]!.id);
    }
  }, [projects, projectId]);

  const canManageTeam = roleHasPermission(role, "MANAGE_PROJECT_MEMBERS");

  return (
    <div>
      <PageHeader
        title="Project Space"
        description="Your team's workspace for assigning tasks, tracking priority and status, and collaborating — per project."
        actions={
          projects && projects.length > 0 ? (
            <Select value={projectId ?? ""} onChange={(e) => setProjectId(e.target.value)} style={{ minWidth: "14rem" }}>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          ) : undefined
        }
      />

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonTable rows={5} />
      ) : !projects || projects.length === 0 ? (
        <EmptyState
          icon={Boxes}
          title="No projects yet"
          description="Create a project first — Project Space will let you assign and track its tasks and team from here."
        />
      ) : !projectId ? (
        <SkeletonTable rows={5} />
      ) : (
        <div>
          <div className="tabs" role="tablist">
            <button type="button" className="tab" aria-current={tab === "board" ? "page" : undefined} onClick={() => setTab("board")}>
              <ClipboardList size={14} aria-hidden /> Board
            </button>
            <button type="button" className="tab" aria-current={tab === "team" ? "page" : undefined} onClick={() => setTab("team")}>
              <Users size={14} aria-hidden /> Team
            </button>
          </div>

          {tab === "board" ? (
            <ProjectTasksView key={projectId} projectId={projectId} showHeader={false} />
          ) : (
            <div style={{ maxWidth: "44rem" }}>
              <ProjectTeamCard key={projectId} projectId={projectId} canManage={canManageTeam} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
