"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { useRequirement } from "@/hooks/useRequirements";
import { formatDateTime, formatPercent } from "@/lib/format";
import { requirementStatusDisplay } from "@/lib/status";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";

export default function RequirementDetailPage() {
  const params = useParams<{ projectId: string; requirementId: string }>();
  const { data, isLoading, error, refetch } = useRequirement(params.requirementId, params.projectId);

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (isLoading || !data) return <SkeletonCard />;

  const { requirement, evidence_links, delivery_records } = data;

  return (
    <div style={{ maxWidth: "44rem" }}>
      <Link href={`/app/projects/${params.projectId}/requirements`} style={{ display: "inline-block", marginBottom: "var(--space-4)", fontSize: "var(--font-size-sm)" }}>
        ← All requirements
      </Link>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)", marginBottom: "var(--space-5)" }}>
        <div>
          <p style={{ margin: 0, fontFamily: "var(--font-family-mono)", fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>
            {requirement.key}
          </p>
          <h1 style={{ margin: "var(--space-1) 0 0", fontSize: "var(--font-size-xl)", fontWeight: "var(--font-weight-semibold)" }}>
            {requirement.title}
          </h1>
        </div>
        <StatusBadge status={requirementStatusDisplay(requirement.status)} />
      </div>

      {requirement.description && (
        <Card style={{ marginBottom: "var(--space-5)" }}>
          <CardBody>
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)", lineHeight: "var(--line-height-relaxed)" }}>{requirement.description}</p>
          </CardBody>
        </Card>
      )}

      {requirement.acceptance_criteria.length > 0 && (
        <Card style={{ marginBottom: "var(--space-5)" }}>
          <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Acceptance criteria</h2>} />
          <CardBody>
            <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "var(--font-size-sm)" }}>
              {requirement.acceptance_criteria.map((c, i) => (
                <li key={i}>{String(c)}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      <Card style={{ marginBottom: "var(--space-5)" }}>
        <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Supporting evidence links ({evidence_links.length})</h2>} />
        <CardBody>
          {evidence_links.length === 0 ? (
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>
              No evidence has been explicitly linked to this requirement yet.
            </p>
          ) : (
            <div style={{ display: "grid", gap: "var(--space-2)" }}>
              {evidence_links.map((link, i) => (
                <div key={i} className="card" style={{ padding: "var(--space-3)", display: "flex", justifyContent: "space-between" }}>
                  <span className="badge badge--neutral">{link.relation_type}</span>
                  {link.confidence !== null && <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>{formatPercent(link.confidence)} confidence</span>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Delivery records ({delivery_records.length})</h2>} />
        <CardBody>
          {delivery_records.length === 0 ? (
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>No delivery records yet.</p>
          ) : (
            <div style={{ display: "grid", gap: "var(--space-2)" }}>
              {delivery_records.map((record) => (
                <div key={record.id} className="card" style={{ padding: "var(--space-3)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span className="badge badge--info">{record.status.replaceAll("_", " ")}</span>
                    {record.verified_at && <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>{formatDateTime(record.verified_at)}</span>}
                  </div>
                  {record.evidence_summary && <p style={{ margin: "var(--space-2) 0 0", fontSize: "var(--font-size-sm)" }}>{record.evidence_summary}</p>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
