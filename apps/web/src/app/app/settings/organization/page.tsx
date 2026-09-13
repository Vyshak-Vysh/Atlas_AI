"use client";

import { useCurrentTenant } from "@/hooks/useCurrentWorkspace";
import { formatDateTime } from "@/lib/format";
import { Card, CardBody } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Field";
import { SkeletonCard } from "@/components/ui/Skeleton";

export default function OrganizationSettingsPage() {
  const { data: tenant, isLoading } = useCurrentTenant();

  if (isLoading || !tenant) return <SkeletonCard />;

  return (
    <Card style={{ maxWidth: "32rem" }}>
      <CardBody>
        <div style={{ display: "grid", gap: "var(--space-4)" }}>
          <Field label="Workspace name" htmlFor="wname" hint="Renaming a workspace isn't supported in this deployment yet.">
            <Input id="wname" value={tenant.name} disabled />
          </Field>
          <Field label="Workspace slug" htmlFor="wslug">
            <Input id="wslug" value={tenant.slug} disabled />
          </Field>
          <Field label="Status" htmlFor="wstatus">
            <Input id="wstatus" value={tenant.status} disabled />
          </Field>
          <Field label="Created" htmlFor="wcreated">
            <Input id="wcreated" value={formatDateTime(tenant.created_at)} disabled />
          </Field>
        </div>
      </CardBody>
    </Card>
  );
}
