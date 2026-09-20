"use client";

import { AlertTriangle, CheckSquare, FolderKanban, Layers, Plus, Sparkles } from "lucide-react";
import Link from "next/link";

import { useAuditEvents } from "@/hooks/useAuditEvents";
import { usePendingApprovalNotifications } from "@/hooks/useNotifications";
import { useProjects } from "@/hooks/useProjects";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useFindingsAcrossProjects } from "@/hooks/useWorkspaceSummary";
import { useSpaces } from "@/hooks/useSpaces";
import { findingStatusDisplay, projectStatusDisplay } from "@/lib/status";
import { formatRelativeTime } from "@/lib/format";
import { ActivityFeed } from "@/components/shell/ActivityFeed";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/Badge";
import { SkeletonLines, SkeletonMetricGrid } from "@/components/ui/Skeleton";

export default function OverviewPage() {
  const { data: user } = useCurrentUser();
  const { data: projects, isLoading: projectsLoading, error: projectsError, refetch } = useProjects();
  const { all: allFindings, isLoading: findingsLoading } = useFindingsAcrossProjects();
  const { items: pendingApprovals } = usePendingApprovalNotifications();
  const { data: auditEvents } = useAuditEvents(15);
  const { data: spaces, isLoading: spacesLoading } = useSpaces();

  const activeProjects = (projects ?? []).filter((p) => p.status === "ACTIVE");
  const conflicting = allFindings.filter((f) => f.finding.status === "CONFLICTING");
  const openFindings = allFindings.filter((f) => !["SUPERSEDED"].includes(f.finding.status));

  const loading = projectsLoading || findingsLoading;

  return (
    <div>
      <PageHeader
        eyebrow={<span className="live-dot">Live</span>}
        title={`Welcome back${user?.display_name ? `, ${user.display_name.split(" ")[0]}` : ""}`}
        description="An operational summary across every project in this workspace."
        actions={
          <Link href="/app/projects/new">
            <Button>
              <Plus size={16} aria-hidden /> New project
            </Button>
          </Link>
        }
      />

      {projectsError ? (
        <ErrorState error={projectsError} onRetry={() => refetch()} />
      ) : loading ? (
        <SkeletonMetricGrid />
      ) : (
        <div className="metric-grid">
          <MetricCard label="Active projects" value={activeProjects.length} icon={FolderKanban} href="/app/projects" />
          <MetricCard
            label="Scope conflicts"
            value={conflicting.length}
            icon={AlertTriangle}
            href="/app/findings"
            meta={conflicting.length > 0 ? "Needs review" : "None open"}
          />
          <MetricCard label="Open findings" value={openFindings.length} icon={Sparkles} href="/app/findings" />
          <MetricCard
            label="Pending approvals"
            value={pendingApprovals.length}
            icon={CheckSquare}
            href="/app/approvals"
            meta={pendingApprovals.length > 0 ? "Waiting on you or your team" : "All clear"}
          />
        </div>
      )}

      <div className="panel-grid" style={{ marginTop: "var(--space-6)" }}>
        <div style={{ display: "grid", gap: "var(--space-5)" }}>
          <Card>
            <CardHeader
              title={<h2 style={{ margin: 0, fontSize: "var(--font-size-lg)", fontWeight: "var(--font-weight-semibold)" }}>Project health</h2>}
              actions={
                <Link href="/app/projects" style={{ fontSize: "var(--font-size-sm)" }}>
                  View all
                </Link>
              }
            />
            <CardBody>
              {loading ? (
                <SkeletonLines count={3} />
              ) : !projects || projects.length === 0 ? (
                <EmptyState
                  icon={FolderKanban}
                  title="No projects yet"
                  description="Create your first project to start connecting evidence and asking scope questions."
                  actions={
                    <Link href="/app/projects/new">
                      <Button size="small">Create project</Button>
                    </Link>
                  }
                />
              ) : (
                <div style={{ display: "grid", gap: "var(--space-3)" }}>
                  {projects.slice(0, 6).map((project) => (
                    <Link
                      key={project.id}
                      href={`/app/projects/${project.id}/overview`}
                      className="card card--interactive"
                      style={{ padding: "var(--space-4)", textDecoration: "none", color: "inherit" }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-3)" }}>
                        <div>
                          <p style={{ margin: 0, fontWeight: "var(--font-weight-medium)" }}>{project.name}</p>
                          {project.client_name && (
                            <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>
                              {project.client_name}
                            </p>
                          )}
                        </div>
                        <StatusBadge status={projectStatusDisplay(project.status)} />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title={<h2 style={{ margin: 0, fontSize: "var(--font-size-lg)", fontWeight: "var(--font-weight-semibold)" }}>Recent findings</h2>}
              actions={
                <Link href="/app/findings" style={{ fontSize: "var(--font-size-sm)" }}>
                  View all
                </Link>
              }
            />
            <CardBody>
              {loading ? (
                <SkeletonLines count={3} />
              ) : allFindings.length === 0 ? (
                <EmptyState
                  icon={Sparkles}
                  title="No findings yet"
                  description="AtlasAI will show findings once evidence is connected and an investigation has run."
                />
              ) : (
                <div style={{ display: "grid", gap: "var(--space-3)" }}>
                  {allFindings
                    .sort((a, b) => new Date(b.finding.created_at).getTime() - new Date(a.finding.created_at).getTime())
                    .slice(0, 5)
                    .map(({ project, finding }) => (
                      <Link
                        key={finding.id}
                        href={`/app/projects/${project.id}/findings/${finding.id}`}
                        style={{ textDecoration: "none", color: "inherit" }}
                      >
                        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-3)", padding: "var(--space-3) 0", borderBottom: "1px solid var(--border-subtle)" }}>
                          <div style={{ minWidth: 0 }}>
                            <p style={{ margin: 0, fontSize: "var(--font-size-sm)", fontWeight: "var(--font-weight-medium)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {finding.summary}
                            </p>
                            <p style={{ margin: "0.15rem 0 0", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
                              {project.name} · {formatRelativeTime(finding.created_at)}
                            </p>
                          </div>
                          <StatusBadge status={findingStatusDisplay(finding.status)} />
                        </div>
                      </Link>
                    ))}
                </div>
              )}
            </CardBody>
          </Card>
        </div>

        <div style={{ display: "grid", gap: "var(--space-5)" }}>
          <Card>
            <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-lg)", fontWeight: "var(--font-weight-semibold)" }}>Recent activity</h2>} />
            <CardBody>
              <ActivityFeed events={auditEvents ?? []} />
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title={<h2 style={{ margin: 0, fontSize: "var(--font-size-lg)", fontWeight: "var(--font-weight-semibold)" }}>Clients</h2>}
              actions={
                <Link href="/app/spaces" style={{ fontSize: "var(--font-size-sm)" }}>
                  View all
                </Link>
              }
            />
            <CardBody>
              {spacesLoading ? (
                <SkeletonLines count={3} />
              ) : !spaces || spaces.length === 0 ? (
                <EmptyState
                  icon={Layers}
                  title="No spaces yet"
                  description="Group a client's projects into a Space to see their findings, evidence, and reports rolled up in one place."
                  actions={
                    <Link href="/app/spaces">
                      <Button size="small">Create a space</Button>
                    </Link>
                  }
                />
              ) : (
                <div style={{ display: "grid", gap: "var(--space-2)" }}>
                  {spaces.slice(0, 6).map((space) => (
                    <Link
                      key={space.id}
                      href={`/app/spaces/${space.id}`}
                      className="card card--interactive"
                      style={{ padding: "var(--space-3) var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-3)", textDecoration: "none", color: "inherit" }}
                    >
                      <span className="sidebar-tree-dot" style={{ background: space.color ?? "var(--color-brand-500)" }} aria-hidden />
                      <span style={{ fontWeight: "var(--font-weight-medium)", fontSize: "var(--font-size-sm)" }}>{space.name}</span>
                    </Link>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
