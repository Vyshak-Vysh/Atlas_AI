"use client";

import { Sparkles } from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";

import { useFindings } from "@/hooks/useFindings";
import { formatPercent, formatRelativeTime } from "@/lib/format";
import { findingStatusDisplay } from "@/lib/status";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonTable } from "@/components/ui/Skeleton";

const STATUS_OPTIONS = [
  "ALL",
  "IN_SCOPE_SUPPORTED",
  "OUT_OF_SCOPE_SUPPORTED",
  "CONFLICTING",
  "AMBIGUOUS",
  "NOT_VERIFIED",
  "DELIVERED_VERIFIED",
  "PARTIAL",
  "SUPERSEDED",
  "PENDING_APPROVAL",
];

export default function FindingsListPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const status = searchParams.get("status") ?? "ALL";

  const { data: findings, isLoading, error, refetch } = useFindings(params.projectId, status === "ALL" ? undefined : status);

  function setStatus(next: string) {
    const url = new URL(window.location.href);
    if (next === "ALL") url.searchParams.delete("status");
    else url.searchParams.set("status", next);
    router.push(url.pathname + url.search);
  }

  return (
    <div>
      <PageHeader title="Findings" description="AI-supported and human-reviewed project findings, each backed by cited evidence." />

      <div style={{ marginBottom: "var(--space-5)" }}>
        <select className="select" style={{ maxWidth: "16rem" }} value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? "All statuses" : findingStatusDisplay(s).label}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonTable rows={6} />
      ) : !findings || findings.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="No findings yet"
          description="AtlasAI will show findings after evidence is connected and an investigation has been completed."
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Summary</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Citations</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {findings
                .slice()
                .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                .map((finding) => (
                  <tr
                    key={finding.id}
                    className="is-clickable"
                    onClick={() => router.push(`/app/projects/${params.projectId}/findings/${finding.id}`)}
                  >
                    <td style={{ maxWidth: "28rem" }}>
                      {finding.summary}
                      {finding.requires_human_review && (
                        <span className="badge badge--warning" style={{ marginLeft: "var(--space-2)" }}>
                          Needs review
                        </span>
                      )}
                    </td>
                    <td>
                      <StatusBadge status={findingStatusDisplay(finding.status)} />
                    </td>
                    <td>{formatPercent(finding.confidence)}</td>
                    <td>{finding.citations.length}</td>
                    <td>{formatRelativeTime(finding.created_at)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
