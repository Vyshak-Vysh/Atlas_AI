"use client";

import { CheckCircle2, Lock, ShieldCheck, XCircle } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { useAction, useApproveAction, useRejectAction, actionErrorMessage } from "@/hooks/useApprovals";
import { formatDateTime } from "@/lib/format";
import { actionStatusDisplay } from "@/lib/status";
import { useToast } from "@/lib/toast";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Field, Textarea } from "@/components/ui/Field";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";

export default function ApprovalDetailPage() {
  const params = useParams<{ projectId: string; actionId: string }>();
  const router = useRouter();
  const { toast } = useToast();
  const { data: action, isLoading, error, refetch } = useAction(params.actionId, params.projectId);
  const approve = useApproveAction(params.projectId);
  const reject = useRejectAction(params.projectId);
  const [reason, setReason] = useState("");
  const [rejecting, setRejecting] = useState(false);

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (isLoading || !action) return <SkeletonCard />;

  const payload = action.payload_json as {
    question?: string;
    draft_body?: string;
    based_on_finding_status?: string;
    citation_count?: number;
  };
  const isPending = action.status === "WAITING_APPROVAL";

  async function handleApprove() {
    try {
      await approve.mutateAsync({ actionId: params.actionId, expectedPayloadHash: action!.payload_hash });
      toast({ title: "Action approved", variant: "success" });
    } catch (err) {
      toast({ title: "Couldn't approve", description: actionErrorMessage(err), variant: "danger" });
    }
  }

  async function handleReject() {
    try {
      await reject.mutateAsync({ actionId: params.actionId, reason: reason.trim() || undefined });
      toast({ title: "Action rejected", variant: "info" });
      setRejecting(false);
    } catch (err) {
      toast({ title: "Couldn't reject", description: actionErrorMessage(err), variant: "danger" });
    }
  }

  return (
    <div style={{ maxWidth: "44rem" }}>
      <button
        type="button"
        onClick={() => router.push(`/app/projects/${params.projectId}/approvals`)}
        style={{ background: "none", border: "none", padding: 0, marginBottom: "var(--space-4)", fontSize: "var(--font-size-sm)", color: "var(--text-link)", cursor: "pointer" }}
      >
        ← All approvals
      </button>

      <div className="approval-card" data-status={action.status}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
          <div>
            <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>Proposed action</p>
            <h1 style={{ margin: "var(--space-1) 0 0", fontSize: "var(--font-size-xl)", fontWeight: "var(--font-weight-semibold)" }}>
              {action.action_type.replaceAll("_", " ")}
            </h1>
          </div>
          <StatusBadge status={actionStatusDisplay(action.status)} />
        </div>

        {payload.question && (
          <div style={{ marginTop: "var(--space-5)" }}>
            <p style={{ margin: 0, fontSize: "var(--font-size-xs)", fontWeight: "var(--font-weight-semibold)", color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Original question
            </p>
            <p style={{ margin: "var(--space-2) 0 0" }}>{payload.question}</p>
          </div>
        )}

        {payload.draft_body && (
          <div style={{ marginTop: "var(--space-5)" }}>
            <p style={{ margin: 0, fontSize: "var(--font-size-xs)", fontWeight: "var(--font-weight-semibold)", color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <Lock size={12} aria-hidden /> Draft response (immutable — payload is hash-locked to what you&apos;re approving)
            </p>
            <div className="card" style={{ marginTop: "var(--space-2)", padding: "var(--space-4)", background: "var(--surface-subtle)" }}>
              <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{payload.draft_body}</p>
            </div>
          </div>
        )}

        <div className="approval-metadata">
          {payload.based_on_finding_status && <MetaItem label="Based on finding" value={payload.based_on_finding_status.replaceAll("_", " ")} />}
          {payload.citation_count !== undefined && <MetaItem label="Citations" value={String(payload.citation_count)} />}
          <MetaItem label="Payload hash" value={`${action.payload_hash.slice(0, 16)}…`} mono />
          <MetaItem label="Proposed" value={formatDateTime(action.created_at)} />
          {action.executed_at && <MetaItem label="Executed" value={formatDateTime(action.executed_at)} />}
        </div>

        {isPending && (
          <>
            <div className="info-callout" style={{ marginTop: "var(--space-5)" }}>
              <ShieldCheck size={16} aria-hidden style={{ flexShrink: 0 }} />
              <span>Approving executes this exact payload immediately. Rejecting requires no further action.</span>
            </div>

            {rejecting && (
              <Field label="Reason for rejection (optional)" htmlFor="reason" hint="Shared in the audit trail.">
                <Textarea id="reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
              </Field>
            )}

            <div className="approval-card__actions">
              {!rejecting ? (
                <>
                  <Button variant="success" onClick={handleApprove} loading={approve.isPending}>
                    <CheckCircle2 size={16} aria-hidden /> Approve
                  </Button>
                  <Button variant="danger" onClick={() => setRejecting(true)}>
                    <XCircle size={16} aria-hidden /> Reject
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="danger" onClick={handleReject} loading={reject.isPending}>
                    Confirm rejection
                  </Button>
                  <Button variant="secondary" onClick={() => setRejecting(false)}>
                    Cancel
                  </Button>
                </>
              )}
            </div>
          </>
        )}

        {action.status === "FAILED" && (
          <div className="error-state" style={{ marginTop: "var(--space-5)" }}>
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>
              Execution failed after approval — most action types (beyond drafting) have no live execution handler in
              this deployment yet.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function MetaItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="approval-metadata__label">{label}</p>
      <p className="approval-metadata__value" style={mono ? { fontFamily: "var(--font-family-mono)" } : undefined}>
        {value}
      </p>
    </div>
  );
}
