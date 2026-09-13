"use client";

import { useParams } from "next/navigation";
import { useMemo } from "react";

import { useAuditEvents } from "@/hooks/useAuditEvents";
import { ActivityFeed } from "@/components/shell/ActivityFeed";
import { PageHeader } from "@/components/shell/PageHeader";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonLines } from "@/components/ui/Skeleton";

export default function ProjectActivityPage() {
  const params = useParams<{ projectId: string }>();
  const { data: events, isLoading, error, refetch } = useAuditEvents(500);

  const projectEvents = useMemo(() => {
    if (!events) return [];
    return events.filter(
      (e) => e.target_id === params.projectId || (e.metadata as { project_id?: string })?.project_id === params.projectId,
    );
  }, [events, params.projectId]);

  return (
    <div>
      <PageHeader
        title="Activity"
        description="Audit events attributable to this project, filtered from the workspace-wide audit log."
      />
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonLines count={6} />
      ) : (
        <>
          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)", marginBottom: "var(--space-4)" }}>
            Some system events aren&rsquo;t tagged with a project and won&rsquo;t appear here — see the full{" "}
            <a href="/app/audit">workspace audit log</a> for everything.
          </p>
          <ActivityFeed events={projectEvents} limit={100} />
        </>
      )}
    </div>
  );
}
