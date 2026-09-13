"use client";

import { CheckSquare } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useActionsAcrossProjects } from "@/hooks/useActionsAcrossProjects";
import { formatRelativeTime } from "@/lib/format";
import { actionStatusDisplay } from "@/lib/status";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/Skeleton";

const STATUS_OPTIONS = ["WAITING_APPROVAL", "ALL", "APPROVED", "REJECTED", "EXECUTED", "EXPIRED", "FAILED"];

export default function GlobalApprovalsPage() {
  const router = useRouter();
  const [status, setStatus] = useState("WAITING_APPROVAL");
  const { all, isLoading } = useActionsAcrossProjects(status === "ALL" ? undefined : status);

  return (
    <div>
      <PageHeader title="Approvals" description="Actions AtlasAI has proposed across every project, waiting for human authorization." />

      <div style={{ marginBottom: "var(--space-5)" }}>
        <select className="select" style={{ maxWidth: "16rem" }} value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? "All statuses" : actionStatusDisplay(s).label}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <SkeletonTable rows={5} />
      ) : all.length === 0 ? (
        <EmptyState icon={CheckSquare} title="Nothing waiting on approval" description="Approvals from any project will show up here." />
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
              {all.map(({ project, action }) => (
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
        </div>
      )}
    </div>
  );
}
