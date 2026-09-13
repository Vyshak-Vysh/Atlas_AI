"use client";

import { FileText, FileUp, Search, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { useFindings } from "@/hooks/useFindings";
import { useProjectOverview } from "@/hooks/useProjects";
import { useSources } from "@/hooks/useSources";
import { useActions } from "@/hooks/useApprovals";
import { formatDate, formatRelativeTime, isStale } from "@/lib/format";
import { findingStatusDisplay, phaseStatusDisplay } from "@/lib/status";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/Badge";
import { SkeletonLines, SkeletonMetricGrid } from "@/components/ui/Skeleton";

const SCOPE_STATUSES = [
  "IN_SCOPE_SUPPORTED",
  "OUT_OF_SCOPE_SUPPORTED",
  "CONFLICTING",
  "AMBIGUOUS",
  "NOT_VERIFIED",
  "DELIVERED_VERIFIED",
  "PARTIAL",
  "PENDING_APPROVAL",
];

export default function ProjectOverviewTab() {
  const params = useParams<{ projectId: string }>();
  const { data: overview, isLoading: overviewLoading } = useProjectOverview(params.projectId);
  const { data: findings, isLoading: findingsLoading } = useFindings(params.projectId);
  const { data: sources, isLoading: sourcesLoading } = useSources(params.projectId);
  const { data: pendingActions } = useActions(params.projectId, "WAITING_APPROVAL");

  const loading = overviewLoading || findingsLoading;
  const scopeCounts = SCOPE_STATUSES.map((status) => ({
    status,
    count: (findings ?? []).filter((f) => f.status === status).length,
  })).filter((s) => s.count > 0);

  const latestSource = (sources ?? []).slice().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

  return (
    <div>
      <div className="page-header__actions" style={{ marginBottom: "var(--space-5)" }}>
        <Link href={`/app/projects/${params.projectId}/investigations`}>
          <Button size="small">
            <Sparkles size={15} aria-hidden /> Start investigation
          </Button>
        </Link>
        <Link href={`/app/projects/${params.projectId}/evidence`}>
          <Button variant="secondary" size="small">
            <FileUp size={15} aria-hidden /> Add evidence
          </Button>
        </Link>
        <Link href={`/app/projects/${params.projectId}/findings`}>
          <Button variant="secondary" size="small">
            <Search size={15} aria-hidden /> Review findings
          </Button>
        </Link>
        <Link href={`/app/projects/${params.projectId}/reports`}>
          <Button variant="secondary" size="small">
            <FileText size={15} aria-hidden /> Export report
          </Button>
        </Link>
      </div>

      {loading ? (
        <SkeletonMetricGrid count={4} />
      ) : (
        <div className="metric-grid">
          <MetricCard label="Phases" value={overview?.phases.length ?? 0} />
          <MetricCard label="Findings" value={findings?.length ?? 0} href={`/app/projects/${params.projectId}/findings`} />
          <MetricCard
            label="Pending approvals"
            value={pendingActions?.length ?? 0}
            href={`/app/projects/${params.projectId}/approvals`}
          />
          <MetricCard label="Team members" value={overview?.member_count ?? 0} href={`/app/projects/${params.projectId}/settings`} />
        </div>
      )}

      <div className="panel-grid" style={{ marginTop: "var(--space-6)" }}>
        <div style={{ display: "grid", gap: "var(--space-5)" }}>
          <Card>
            <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-lg)", fontWeight: "var(--font-weight-semibold)" }}>Scope summary</h2>} />
            <CardBody>
              {loading ? (
                <SkeletonLines count={3} />
              ) : scopeCounts.length === 0 ? (
                <EmptyState
                  icon={Sparkles}
                  title="No findings yet"
                  description="AtlasAI will show findings after evidence is connected and an investigation has run."
                  actions={
                    <Link href={`/app/projects/${params.projectId}/investigations`}>
                      <Button size="small">Start investigation</Button>
                    </Link>
                  }
                />
              ) : (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)" }}>
                  {scopeCounts.map(({ status, count }) => (
                    <Link
                      key={status}
                      href={`/app/projects/${params.projectId}/findings?status=${status}`}
                      style={{ textDecoration: "none" }}
                    >
                      <div className="card" style={{ padding: "var(--space-3) var(--space-4)", minWidth: "9rem" }}>
                        <StatusBadge status={findingStatusDisplay(status)} />
                        <p style={{ margin: "var(--space-2) 0 0", fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-semibold)" }}>
                          {count}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title={<h2 style={{ margin: 0, fontSize: "var(--font-size-lg)", fontWeight: "var(--font-weight-semibold)" }}>Phase progress</h2>}
            />
            <CardBody>
              {overviewLoading ? (
                <SkeletonLines count={2} />
              ) : !overview || overview.phases.length === 0 ? (
                <EmptyState title="No phases yet" description="Add phases from project settings to track delivery progress." />
              ) : (
                <div className="timeline">
                  {overview.phases
                    .slice()
                    .sort((a, b) => a.phase_number - b.phase_number)
                    .map((phase) => (
                      <div key={phase.id} className="timeline-item">
                        <div className="timeline-item__rail" />
                        <div>
                          <p className="timeline-item__title">
                            Phase {phase.phase_number}: {phase.name}
                          </p>
                          <p className="timeline-item__description">
                            {phase.start_date && formatDate(phase.start_date)}
                            {phase.start_date && phase.end_date && " – "}
                            {phase.end_date && formatDate(phase.end_date)}
                          </p>
                        </div>
                        <StatusBadge status={phaseStatusDisplay(phase.status)} />
                      </div>
                    ))}
                </div>
              )}
            </CardBody>
          </Card>
        </div>

        <div style={{ display: "grid", gap: "var(--space-5)" }}>
          <Card>
            <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-lg)", fontWeight: "var(--font-weight-semibold)" }}>Evidence freshness</h2>} />
            <CardBody>
              {sourcesLoading ? (
                <SkeletonLines count={2} />
              ) : !sources || sources.length === 0 ? (
                <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>
                  No evidence connected yet.
                </p>
              ) : (
                <>
                  <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>
                    {sources.length} source{sources.length === 1 ? "" : "s"} indexed
                  </p>
                  {latestSource && (
                    <p style={{ margin: "var(--space-2) 0 0", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
                      Most recent: {formatRelativeTime(latestSource.created_at)}
                    </p>
                  )}
                  {latestSource && isStale(latestSource.created_at, 24 * 14) && (
                    <div className="stale-banner" style={{ marginTop: "var(--space-3)" }}>
                      Evidence hasn&rsquo;t been updated in over two weeks — findings may not reflect the latest state.
                    </div>
                  )}
                </>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
