"use client";

import { Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import { useAddProjectMember, useProjectMembers, useRemoveProjectMember, useUpdateProjectMemberRole } from "@/hooks/useTeam";
import { ApiError } from "@/lib/api";
import { ALL_ROLES, ROLE_LABELS } from "@/lib/permissions";
import { useToast } from "@/lib/toast";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input, Select } from "@/components/ui/Field";
import { SkeletonLines } from "@/components/ui/Skeleton";

/**
 * Project team roster with role assignment — collaboration/team-editor
 * surface reused by both the per-project Settings page and the
 * "My Work" hub, rather than building a second team-editing UI.
 */
export function ProjectTeamCard({ projectId, canManage }: { projectId: string; canManage: boolean }) {
  const { data: members, isLoading, error: membersError, refetch } = useProjectMembers(projectId);
  const addMember = useAddProjectMember(projectId);
  const updateRole = useUpdateProjectMemberRole(projectId);
  const removeMember = useRemoveProjectMember(projectId);
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("DELIVERY_TEAM");
  const [error, setError] = useState<string | null>(null);
  const [removeTarget, setRemoveTarget] = useState<{ userId: string; name: string } | null>(null);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await addMember.mutateAsync({ email: email.trim(), role });
      setEmail("");
      toast({ title: "Member added", variant: "success" });
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail ?? err.message) : "Failed to add member.");
    }
  }

  return (
    <Card>
      <CardHeader title={<h2 style={{ margin: 0, fontSize: "var(--font-size-md)", fontWeight: "var(--font-weight-semibold)" }}>Team</h2>} />
      <CardBody>
        {membersError ? (
          <ErrorState error={membersError} onRetry={() => refetch()} />
        ) : isLoading ? (
          <SkeletonLines count={3} />
        ) : (
          <div style={{ display: "grid", gap: "var(--space-3)" }}>
            {(members ?? []).map((member) => (
              <div key={member.user_id} style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <Avatar name={member.display_name} size={28} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontSize: "var(--font-size-sm)", fontWeight: "var(--font-weight-medium)" }}>{member.display_name}</p>
                  <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)" }}>{member.email}</p>
                </div>
                {canManage ? (
                  <>
                    <Select
                      value={member.role}
                      onChange={(e) => updateRole.mutate({ userId: member.user_id, role: e.target.value })}
                      style={{ maxWidth: "11rem" }}
                    >
                      {ALL_ROLES.map((r) => (
                        <option key={r} value={r}>
                          {ROLE_LABELS[r]}
                        </option>
                      ))}
                    </Select>
                    <Button
                      variant="ghost"
                      size="small"
                      onClick={() => setRemoveTarget({ userId: member.user_id, name: member.display_name })}
                      aria-label={`Remove ${member.display_name}`}
                    >
                      <Trash2 size={14} aria-hidden />
                    </Button>
                  </>
                ) : (
                  <span className="badge badge--neutral">{ROLE_LABELS[member.role as keyof typeof ROLE_LABELS] ?? member.role}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {canManage && (
          <form onSubmit={handleAdd} style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-4)", borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-4)" }}>
            <Input type="email" placeholder="teammate@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required style={{ flex: 1 }} />
            <Select value={role} onChange={(e) => setRole(e.target.value)} style={{ maxWidth: "11rem" }}>
              {ALL_ROLES.map((r) => (
                <option key={r} value={r}>
                  {ROLE_LABELS[r]}
                </option>
              ))}
            </Select>
            <Button type="submit" loading={addMember.isPending}>
              Add
            </Button>
          </form>
        )}
        {error && <p style={{ color: "var(--color-danger-700)", fontSize: "var(--font-size-sm)", marginTop: "var(--space-2)" }}>{error}</p>}
        <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-tertiary)", marginTop: "var(--space-2)" }}>
          The person must already belong to this workspace — add them from Team settings first if not.
        </p>
      </CardBody>

      <ConfirmDialog
        open={!!removeTarget}
        onClose={() => setRemoveTarget(null)}
        title="Remove team member?"
        description={`${removeTarget?.name} will lose access to this project.`}
        confirmLabel="Remove"
        onConfirm={async () => {
          if (removeTarget) await removeMember.mutateAsync(removeTarget.userId);
        }}
      />
    </Card>
  );
}
