"use client";

import { Sparkles } from "lucide-react";
import { useRouter, useParams } from "next/navigation";
import { useState } from "react";

import { useSpaceFindings } from "@/hooks/useSpaces";
import { formatPercent, formatRelativeTime } from "@/lib/format";
import { findingStatusDisplay } from "@/lib/status";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { SkeletonTable } from "@/components/ui/Skeleton";

const STATUS_OPTIONS = [
  "ALL", "PROPOSED", "IN_SCOPE_SUPPORTED", "OUT_OF_SCOPE_SUPPORTED", "CONFLICTING", "AMBIGUOUS", "SUPERSEDED",
];

/** Every finding across every project in this client's Space, in one
 * place — the rollup that a per-project or all-clients-mixed-together view
 * can't answer: "what has AtlasAI found for this client so far." */
export default function SpaceFindingsPage() {
  const params = useParams<{ spaceId: string }>();
  const router = useRouter();
  const [status, setStatus] = useState("ALL");
  const [page, setPage] = useState(1);
  const { data: items, isLoading, error, refetch } = useSpaceFindings(params.spaceId, status === "ALL" ? undefined : status);
  const { pageRows, page: currentPage, pageCount } = usePagination(items ?? [], page, setPage);

  return (
    <div>
      <div style={{ marginBottom: "var(--space-5)" }}>
        <select
          className="select"
          style={{ maxWidth: "16rem" }}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
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
      ) : !items || items.length === 0 ? (
        <EmptyState icon={Sparkles} title="No findings yet" description="Findings will appear here once an investigation runs on any project in this space." />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Summary</th>
                <th>Project</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map(({ project, finding }) => (
                <tr key={finding.id} className="is-clickable" onClick={() => router.push(`/app/projects/${project.id}/findings/${finding.id}`)}>
                  <td style={{ maxWidth: "26rem" }}>{finding.summary}</td>
                  <td>{project.name}</td>
                  <td>
                    <StatusBadge status={findingStatusDisplay(finding.status)} />
                  </td>
                  <td>{formatPercent(finding.confidence)}</td>
                  <td>{formatRelativeTime(finding.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={currentPage} pageCount={pageCount} onPageChange={setPage} totalItems={items.length} pageSize={25} />
        </div>
      )}
    </div>
  );
}
