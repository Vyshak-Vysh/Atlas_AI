"use client";

import { Plus, Trash2, UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";

import { useCurrentRole } from "@/hooks/useCurrentWorkspace";
import { useAddTenantMember, useRemoveTenantMember, useTenantMembers, useUpdateTenantMemberRole } from "@/hooks/useTeam";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { ALL_ROLES, ROLE_LABELS } from "@/lib/permissions";
import { PageHeader } from "@/components/shell/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Dialog } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Field, Input, Select } from "@/components/ui/Field";
import { SkeletonTable } from "@/components/ui/Skeleton";

export default function TeamPage() {
  const { data: members, isLoading, error, refetch } = useTenantMembers();
  const role = useCurrentRole();
  const isAdmin = role === "AI_ENGINEER_ADMIN";
  const updateRole = useUpdateTenantMemberRole();
  const removeMember = useRemoveTenantMember();
  const [showInvite, setShowInvite] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<{ userId: string; name: string } | null>(null);

  return (
    <div>
      <PageHeader
        title="Team"
        description="Everyone with access to this workspace."
        actions={
          isAdmin && (
            <Button onClick={() => setShowInvite(true)}>
              <Plus size={16} aria-hidden /> Add member
            </Button>
          )
        }
      />

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <SkeletonTable rows={4} />
      ) : !members || members.length === 0 ? (
        <EmptyState icon={UserPlus} title="No members yet" />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>Role</th>
                <th>Joined</th>
                {isAdmin && <th />}
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.user_id}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                      <Avatar name={m.display_name} size={28} />
                      <div>
                        <p style={{ margin: 0, fontWeight: "var(--font-weight-medium)" }}>{m.display_name}</p>
                        <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>{m.email}</p>
                      </div>
                    </div>
                  </td>
                  <td>
                    {isAdmin ? (
                      <Select
                        value={m.role}
                        onChange={(e) => updateRole.mutate({ userId: m.user_id, role: e.target.value })}
                        style={{ maxWidth: "11rem" }}
                      >
                        {ALL_ROLES.map((r) => (
                          <option key={r} value={r}>
                            {ROLE_LABELS[r]}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      <span className="badge badge--neutral">{ROLE_LABELS[m.role as keyof typeof ROLE_LABELS] ?? m.role}</span>
                    )}
                  </td>
                  <td>{formatDate(m.joined_at)}</td>
                  {isAdmin && (
                    <td>
                      <Button variant="ghost" size="small" onClick={() => setRemoveTarget({ userId: m.user_id, name: m.display_name })}>
                        <Trash2 size={14} aria-hidden />
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <InviteDialog open={showInvite} onClose={() => setShowInvite(false)} />

      <ConfirmDialog
        open={!!removeTarget}
        onClose={() => setRemoveTarget(null)}
        title="Remove from workspace?"
        description={`${removeTarget?.name} will lose access to every project in this workspace.`}
        confirmLabel="Remove"
        onConfirm={async () => {
          if (removeTarget) await removeMember.mutateAsync(removeTarget.userId);
        }}
      />
    </div>
  );
}

function InviteDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const addMember = useAddTenantMember();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("DELIVERY_TEAM");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await addMember.mutateAsync({ email: email.trim(), role });
      setEmail("");
      onClose();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 404
            ? "No user with that email exists yet — they need to create an AtlasAI account first."
            : String(err.detail ?? err.message)
          : "Failed to add member.",
      );
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Add a team member">
      <form onSubmit={handleSubmit} style={{ display: "grid", gap: "var(--space-4)" }}>
        {error && (
          <div className="error-state">
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)" }}>{error}</p>
          </div>
        )}
        <Field label="Email" htmlFor="invite-email">
          <Input id="invite-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Role" htmlFor="invite-role">
          <Select id="invite-role" value={role} onChange={(e) => setRole(e.target.value)}>
            {ALL_ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </Select>
        </Field>
        <Button type="submit" loading={addMember.isPending} fullWidth>
          Add to workspace
        </Button>
      </form>
    </Dialog>
  );
}
