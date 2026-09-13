"use client";

import { useEffect, useState } from "react";

import { useCurrentUser } from "@/hooks/useCurrentUser";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/lib/toast";
import { useQueryClient } from "@tanstack/react-query";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Field";
import { SkeletonCard } from "@/components/ui/Skeleton";

export default function ProfileSettingsPage() {
  const { data: user, isLoading } = useCurrentUser();
  const { session } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) setDisplayName(user.display_name);
  }, [user]);

  if (isLoading || !user) return <SkeletonCard />;

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateMe({ display_name: displayName.trim() });
      await queryClient.invalidateQueries({ queryKey: ["me", session?.userId] });
      toast({ title: "Profile updated", variant: "success" });
    } catch (err) {
      toast({ title: "Couldn't save", description: err instanceof ApiError ? String(err.detail) : undefined, variant: "danger" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card style={{ maxWidth: "32rem" }}>
      <CardBody>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", marginBottom: "var(--space-5)" }}>
          <Avatar name={user.display_name} size={48} />
          <div>
            <p style={{ margin: 0, fontWeight: "var(--font-weight-semibold)" }}>{user.display_name}</p>
            <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>{user.email}</p>
          </div>
        </div>
        <div style={{ display: "grid", gap: "var(--space-4)" }}>
          <Field label="Display name" htmlFor="display-name">
            <Input id="display-name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </Field>
          <Field label="Email" htmlFor="email" hint="Email changes aren't supported in this deployment yet.">
            <Input id="email" value={user.email} disabled />
          </Field>
          <Button onClick={handleSave} loading={saving} disabled={!displayName.trim()} style={{ justifySelf: "start" }}>
            Save changes
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
