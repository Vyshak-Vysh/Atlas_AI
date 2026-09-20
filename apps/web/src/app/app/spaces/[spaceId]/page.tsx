"use client";

import { AlertTriangle, CheckSquare, FolderKanban, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { useSpaceOverview, useSpaceProjects, useSpaceReport } from "@/hooks/useSpaces";
import { formatDate } from "@/lib/format";
import { projectStatusDisplay } from "@/lib/status";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";
import { SkeletonMetricGrid, SkeletonTable } from "@/components/ui/Skeleton";

export default function SpaceOverviewPage() {
  const params = useParams<{ spaceId: string }>();
  const spaceId = params.spaceId;

  const { data: overview } = useSpaceOverview(spaceId);
  const { data: projects, isLoading: projectsLoading } = useSpaceProjects(spaceId);
  const { data: report, isLoading: reportLoading } = useSpaceReport(spaceId);

  const conflicting = (report?.findings_by_status ?? []).find((s) => s.status === "CONFLICTING")?.count ?? 0;

  return (
    <div>
      {reportLoading || !report ? (
        <SkeletonMetricGrid />
      ) : (
        <div className="metric-grid" style={{ marginBottom: "var(--space-6)" }}>
          <MetricCard label="Projects" value={report.project_count} icon={FolderKanban} />
          <MetricCard
            label="Scope conflicts"
            value={conflicting}
            icon={AlertTriangle}
            href={`/app/spaces/${spaceId}/findings`}
            meta={conflicting > 0 ? "Needs review" : "None open"}
          />
          <MetricCard label="Open findings" value={report.total_findings} icon={Sparkles} href={`/app/spaces/${spaceId}/findings`} />
          <MetricCard
            label="Pending approvals"
            value={report.total_pending_approvals}
            icon={CheckSquare}
            href={`/app/spaces/${spaceId}/approvals`}
            meta={report.total_pending_approvals > 0 ? "Waiting on your team" : "All clear"}
          />
        </div>
      )}

      {projectsLoading ? (
        <SkeletonTable rows={4} />
      ) : !projects || projects.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects in this space yet"
          description="Create a project inside this space, or move an existing project into it from its settings."
          actions={
            <Link href={`/app/projects/new?spaceId=${spaceId}`}>
              <Button size="small">New project</Button>
            </Link>
          }
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Client</th>
                <th>Tasks delivered</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => {
                const summary = report?.projects.find((p) => p.project.id === project.id);
                return (
                  <tr key={project.id}>
                    <td>
                      <Link
                        href={`/app/projects/${project.id}/overview`}
                        style={{ fontWeight: "var(--font-weight-medium)", color: "var(--text-primary)" }}
                      >
                        {project.name}
                      </Link>
                    </td>
                    <td>{project.client_name ?? overview?.space.name ?? "—"}</td>
                    <td>{summary ? `${summary.requirements_delivered} / ${summary.total_requirements}` : "—"}</td>
                    <td>
                      <StatusBadge status={projectStatusDisplay(project.status)} />
                    </td>
                    <td>{formatDate(project.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
