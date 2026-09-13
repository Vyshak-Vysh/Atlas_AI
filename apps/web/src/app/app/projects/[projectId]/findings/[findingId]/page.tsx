"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { useFinding } from "@/hooks/useFindings";
import { FindingPanel } from "@/components/finding/FindingPanel";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";

export default function FindingDetailPage() {
  const params = useParams<{ projectId: string; findingId: string }>();
  const { data: finding, isLoading, error, refetch } = useFinding(params.findingId, params.projectId);

  return (
    <div style={{ maxWidth: "48rem" }}>
      <Link
        href={`/app/projects/${params.projectId}/findings`}
        style={{ display: "inline-block", marginBottom: "var(--space-4)", fontSize: "var(--font-size-sm)" }}
      >
        ← All findings
      </Link>

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading || !finding ? (
        <SkeletonCard />
      ) : (
        <>
          <FindingPanel finding={finding} />
          <p style={{ marginTop: "var(--space-3)", fontSize: "var(--font-size-sm)" }}>
            <Link href={`/app/projects/${params.projectId}/investigations/${finding.agent_run_id}`}>
              View the investigation that produced this finding →
            </Link>
          </p>
        </>
      )}
    </div>
  );
}
