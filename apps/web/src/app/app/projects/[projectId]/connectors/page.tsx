"use client";

import { CheckCircle2, FileUp, GitBranch, Kanban, Mail, MessageSquare, Plug } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import type { LucideIcon } from "lucide-react";

import { useConnectors, useCreateConnector, useRevokeConnector } from "@/hooks/useConnectors";
import { formatRelativeTime } from "@/lib/format";
import { connectorStatusDisplay } from "@/lib/status";
import { useToast } from "@/lib/toast";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";

const PROVIDER_ICONS: Record<string, LucideIcon> = {
  MANUAL_UPLOAD: FileUp,
  GIT_CI_GITHUB: GitBranch,
  GMAIL: Mail,
  MSGRAPH: Mail,
  GOOGLE_DRIVE: FileUp,
  MEETINGS: MessageSquare,
  PM_JIRA: Kanban,
};

export default function ConnectorsPage() {
  const params = useParams<{ projectId: string }>();
  const { data: connectors, isLoading, error, refetch } = useConnectors(params.projectId);
  const createConnector = useCreateConnector(params.projectId);
  const revokeConnector = useRevokeConnector(params.projectId);
  const { toast } = useToast();
  const [revokeTargetId, setRevokeTargetId] = useState<string | null>(null);

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;

  return (
    <div>
      <PageHeader
        title="Connectors"
        description="Sources this project can pull evidence from. Only providers with a configured adapter can be connected."
      />

      {isLoading || !connectors ? (
        <SkeletonCard />
      ) : (
        <div className="connector-grid">
          {connectors.map((info) => {
            const Icon = PROVIDER_ICONS[info.provider] ?? Plug;
            const isConnected = info.connector?.status === "ACTIVE";
            return (
              <div key={info.provider} className={info.is_available ? "connector-card" : "connector-card connector-card--unavailable"}>
                <div className="connector-card__header">
                  <span className="connector-card__icon">
                    <Icon size={20} aria-hidden />
                  </span>
                  <div>
                    <p className="connector-card__title">{info.display_name}</p>
                    {info.connector && <StatusBadge status={connectorStatusDisplay(info.connector.status)} />}
                  </div>
                </div>
                <p className="connector-card__description">
                  {info.is_available
                    ? info.provider === "MANUAL_UPLOAD"
                      ? "Upload documents directly from the Evidence tab, or activate the connector here."
                      : "Configured for this deployment."
                    : "Requires OAuth credentials an administrator hasn't configured for this deployment yet."}
                </p>
                {info.connector?.last_sync_at && (
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)", margin: 0 }}>
                    Last synced {formatRelativeTime(info.connector.last_sync_at)}
                  </p>
                )}
                <div className="connector-card__footer">
                  {!info.is_available ? (
                    <Button variant="secondary" size="small" disabled>
                      Not configured
                    </Button>
                  ) : isConnected ? (
                    <Button
                      variant="ghost"
                      size="small"
                      onClick={() => setRevokeTargetId(info.connector!.id)}
                      style={{ color: "var(--color-danger-700)" }}
                    >
                      Disconnect
                    </Button>
                  ) : (
                    <Button
                      size="small"
                      loading={createConnector.isPending}
                      onClick={async () => {
                        try {
                          await createConnector.mutateAsync({ provider: info.provider });
                          toast({ title: `${info.display_name} connected`, variant: "success" });
                        } catch {
                          toast({ title: "Couldn't connect", variant: "danger" });
                        }
                      }}
                    >
                      Connect
                    </Button>
                  )}
                  {isConnected && (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)", fontSize: "var(--font-size-xs)", color: "var(--color-success-700)" }}>
                      <CheckCircle2 size={13} aria-hidden /> Active
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <ConfirmDialog
        open={!!revokeTargetId}
        onClose={() => setRevokeTargetId(null)}
        title="Disconnect this source?"
        description="Already-imported evidence stays searchable, but no new content will be synced from this connector until it's reconnected."
        confirmLabel="Disconnect"
        onConfirm={async () => {
          if (revokeTargetId) await revokeConnector.mutateAsync(revokeTargetId);
        }}
      />
    </div>
  );
}
