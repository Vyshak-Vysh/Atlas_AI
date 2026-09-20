"use client";

import { Layers, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useSpaces } from "@/hooks/useSpaces";
import { spaceStatusDisplay } from "@/lib/status";
import { CreateSpaceDialog } from "@/components/spaces/CreateSpaceDialog";
import { PageHeader } from "@/components/shell/PageHeader";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";

export default function SpacesListPage() {
  const { data: spaces, isLoading, error, refetch } = useSpaces();
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div>
      <PageHeader
        title="Spaces"
        description="Group related projects together, ClickUp-style — each Space can hold many projects and their own task workflows."
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus size={16} aria-hidden /> New space
          </Button>
        }
      />

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="connector-grid">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : !spaces || spaces.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="No spaces yet"
          description="Create a Space to organize a group of related projects and their task boards."
          actions={
            <Button size="small" onClick={() => setShowCreate(true)}>
              Create space
            </Button>
          }
        />
      ) : (
        <div className="connector-grid">
          {spaces.map((space) => (
            <Link key={space.id} href={`/app/spaces/${space.id}`} style={{ textDecoration: "none", color: "inherit" }}>
              <Card interactive>
                <CardBody>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                    <span
                      aria-hidden
                      style={{
                        width: "0.75rem",
                        height: "0.75rem",
                        borderRadius: "var(--radius-full)",
                        background: space.color ?? "var(--color-brand-600)",
                        flexShrink: 0,
                      }}
                    />
                    <h3 style={{ margin: 0, fontSize: "var(--font-size-md)" }}>{space.name}</h3>
                  </div>
                  {space.description && (
                    <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-3)" }}>
                      {space.description}
                    </p>
                  )}
                  <StatusBadge status={spaceStatusDisplay(space.status)} />
                </CardBody>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <CreateSpaceDialog open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  );
}
