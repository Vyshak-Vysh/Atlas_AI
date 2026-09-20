"use client";

import { CheckSquare } from "lucide-react";
import { useRouter, useParams } from "next/navigation";
import { useState } from "react";

import { useSpaceActions } from "@/hooks/useSpaces";
import { formatRelativeTime } from "@/lib/format";
import { actionStatusDisplay } from "@/lib/status";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { SkeletonTable } from "@/components/ui/Skeleton";

const STATUS_OPTIONS = ["WAITING_APPROVAL", "ALL", "APPROVED", "REJECTED", "EXECUTED", "EXPIRED", "FAILED"];

/** Every action awaiting approval across every project in this client's
 * Space — so approving Amazon's work doesn't mean checking three separate
 * project tabs one at a time. */
export default function SpaceApprovalsPage() {
  const params = useParams<{ spaceId: string }>();
  const router = useRouter();
  const [status, setStatus] = useState("WAITING_APPROVAL");
  const [page, setPage] = useState(1);
  const { data: items, isLoading, error, refetch } = useSpaceActions(params.spaceId, status === "ALL" ? undefined : status);
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
              {s === "ALL" ? "All statuses" : actionStatusDisplay(s).label}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonTable rows={5} />
      ) : !items || items.length === 0 ? (
        <EmptyState icon={CheckSquare} title="Nothing waiting on approval" description="Approvals from any project in this space will show up here." />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Project</th>
                <th>Status</th>
                <th>Requested</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map(({ project, action }) => (
                <tr key={action.id} className="is-clickable" onClick={() => router.push(`/app/projects/${project.id}/approvals/${action.id}`)}>
                  <td>{action.action_type.replaceAll("_", " ")}</td>
                  <td>{project.name}</td>
                  <td>
                    <StatusBadge status={actionStatusDisplay(action.status)} />
                  </td>
                  <td>{formatRelativeTime(action.created_at)}</td>
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
