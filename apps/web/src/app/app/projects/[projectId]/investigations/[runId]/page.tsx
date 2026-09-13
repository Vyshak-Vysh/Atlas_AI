"use client";

import { AlertOctagon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { useAgentRun } from "@/hooks/useAgentRuns";
import { useFinding } from "@/hooks/useFindings";
import { useInvestigationStream } from "@/hooks/useInvestigationStream";
import { agentRunStatusDisplay } from "@/lib/status";
import { FindingPanel } from "@/components/finding/FindingPanel";
import { InvestigationProgress } from "@/components/investigation/InvestigationProgress";
import { Card, CardBody } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/Badge";
import { SkeletonCard } from "@/components/ui/Skeleton";

const ACTIVE_STATUSES = ["RECEIVED", "RUNNING", "WAITING_APPROVAL"];

export default function InvestigationDetailPage() {
  const params = useParams<{ projectId: string; runId: string }>();
  const { data: run, isLoading, error, refetch } = useAgentRun(params.runId, params.projectId);
  const isActive = run ? ACTIVE_STATUSES.includes(run.status) : true;
  const stream = useInvestigationStream(isActive ? params.runId : undefined, params.projectId);
  const { data: finding, isLoading: findingLoading } = useFinding(
    run?.finding_id ?? undefined,
    params.projectId,
  );

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (isLoading || !run) return <SkeletonCard />;

  return (
    <div style={{ maxWidth: "48rem" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)", marginBottom: "var(--space-5)" }}>
        <div>
          <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>Question</p>
          <h1 style={{ margin: "var(--space-1) 0 0", fontSize: "var(--font-size-xl)", fontWeight: "var(--font-weight-semibold)" }}>
            {run.question}
          </h1>
        </div>
        <StatusBadge status={agentRunStatusDisplay(run.status)} />
      </div>

      {isActive && (
        <Card>
          <CardBody>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-4)" }}>
              <p style={{ margin: 0, fontWeight: "var(--font-weight-semibold)", fontSize: "var(--font-size-sm)" }}>Investigation progress</p>
              <span className={stream.connected ? "live-dot" : "live-dot live-dot--stale"}>
                {stream.connected ? "Live" : "Reconnecting…"}
              </span>
            </div>
            <InvestigationProgress steps={stream.steps} failed={stream.failed} />
          </CardBody>
        </Card>
      )}

      {run.status === "FAILED" && (
        <div className="error-state" style={{ marginTop: "var(--space-5)" }}>
          <AlertOctagon size={18} aria-hidden style={{ flexShrink: 0, marginTop: "0.1rem" }} />
          <div>
            <p style={{ margin: 0, fontWeight: "var(--font-weight-semibold)" }}>This investigation failed</p>
            <p style={{ margin: "var(--space-1) 0 0", fontSize: "var(--font-size-sm)" }}>
              {run.error ?? "No further detail was recorded for this failure."}
            </p>
            <p style={{ margin: "var(--space-2) 0 0", fontSize: "var(--font-size-xs)" }}>
              This is a retrieval/analysis failure, not evidence that the answer is out of scope — retry once the
              underlying issue is resolved.
            </p>
          </div>
        </div>
      )}

      {run.status === "COMPLETED" && (
        <div style={{ marginTop: "var(--space-5)" }}>
          {findingLoading ? (
            <SkeletonCard />
          ) : finding ? (
            <FindingPanel finding={finding} />
          ) : (
            <p style={{ color: "var(--text-tertiary)", fontSize: "var(--font-size-sm)" }}>
              This investigation completed without producing a citable finding.
            </p>
          )}
          {finding && (
            <p style={{ marginTop: "var(--space-3)", fontSize: "var(--font-size-sm)" }}>
              <Link href={`/app/projects/${params.projectId}/findings/${finding.id}`}>Open in Findings →</Link>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
