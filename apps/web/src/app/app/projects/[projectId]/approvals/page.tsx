"use client";

import { CheckSquare } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { useActions } from "@/hooks/useApprovals";
import { formatRelativeTime } from "@/lib/format";
import { actionStatusDisplay } from "@/lib/status";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonTable } from "@/components/ui/Skeleton";

const STATUS_OPTIONS = ["ALL", "WAITING_APPROVAL", "APPROVED", "REJECTED", "EXECUTED", "EXPIRED", "FAILED"];

export default function ApprovalsListPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const [status, setStatus] = useState("WAITING_APPROVAL");
  const { data: actions, isLoading, error, refetch } = useActions(params.projectId, status === "ALL" ? undefined : status);

  return (
    <div>
      <PageHeader title="Approvals" description="Consequential actions AtlasAI has proposed, waiting for human authorization." />

      <div style={{ marginBottom: "var(--space-5)" }}>
        <select className="select" style={{ maxWidth: "16rem" }} value={status} onChange={(e) => setStatus(e.target.value)}>
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
      ) : !actions || actions.length === 0 ? (
        <EmptyState
          icon={CheckSquare}
          title={status === "WAITING_APPROVAL" ? "Nothing waiting on approval" : "No matching approvals"}
          description="Actions AtlasAI proposes during an investigation — like drafting a client response — appear here for review."
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Status</th>
                <th>Requested</th>
              </tr>
            </thead>
            <tbody>
              {actions
                .slice()
                .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                .map((action) => (
                  <tr
                    key={action.id}
                    className="is-clickable"
                    onClick={() => router.push(`/app/projects/${params.projectId}/approvals/${action.id}`)}
                  >
                    <td>{action.action_type.replaceAll("_", " ")}</td>
                    <td>
                      <StatusBadge status={actionStatusDisplay(action.status)} />
                    </td>
                    <td>{formatRelativeTime(action.created_at)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
