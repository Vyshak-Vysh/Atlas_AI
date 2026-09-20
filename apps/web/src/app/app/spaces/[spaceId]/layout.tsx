"use client";

import { MoreHorizontal, Pencil, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { usePathname, useParams, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { useDeleteSpace, useSpaceOverview } from "@/hooks/useSpaces";
import { ApiError } from "@/lib/api";
import { spaceNav } from "@/lib/nav";
import { spaceStatusDisplay } from "@/lib/status";
import { useToast } from "@/lib/toast";
import { EditSpaceDialog } from "@/components/spaces/EditSpaceDialog";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { DropdownMenu, MenuItem } from "@/components/ui/DropdownMenu";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";

/** Shell for every Space tab (Overview/Findings/Evidence/Reports/Approvals)
 * — the client-level header, edit/delete actions, and tab bar live here
 * exactly once, mirroring projects/[projectId]/layout.tsx one level up. */
export default function SpaceLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ spaceId: string }>();
  const spaceId = params.spaceId;
  const pathname = usePathname();
  const router = useRouter();
  const { toast } = useToast();

  const { data: overview, isLoading, error, refetch } = useSpaceOverview(spaceId);
  const deleteSpace = useDeleteSpace();

  const [showEdit, setShowEdit] = useState(false);
  const [showDelete, setShowDelete] = useState(false);

  if (error) return <ErrorState error={error} onRetry={() => refetch()} title="Couldn't load this space" />;

  const hasProjects = (overview?.project_count ?? 0) > 0;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)", marginBottom: "var(--space-2)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          {isLoading || !overview ? (
            <Skeleton style={{ height: "1.75rem", width: "16rem" }} />
          ) : (
            <>
              <h1 style={{ margin: 0, fontSize: "var(--font-size-2xl)", fontWeight: "var(--font-weight-semibold)" }}>
                {overview.space.name}
              </h1>
              <StatusBadge status={spaceStatusDisplay(overview.space.status)} />
            </>
          )}
        </div>

        {overview && (
          <div style={{ display: "flex", gap: "var(--space-2)", flexShrink: 0 }}>
            <Link href={`/app/projects/new?spaceId=${spaceId}`}>
              <Button size="small">
                <Plus size={14} aria-hidden /> New project
              </Button>
            </Link>
            <DropdownMenu
              trigger={
                <Button variant="secondary" size="icon" aria-label="Space actions">
                  <MoreHorizontal size={16} aria-hidden />
                </Button>
              }
            >
              <MenuItem icon={<Pencil size={14} aria-hidden />} onClick={() => setShowEdit(true)}>
                Edit space
              </MenuItem>
              <MenuItem icon={<Trash2 size={14} aria-hidden />} danger onClick={() => setShowDelete(true)}>
                Delete space
              </MenuItem>
            </DropdownMenu>
          </div>
        )}
      </div>

      {overview?.space.description && (
        <p style={{ margin: "0 0 var(--space-4)", color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", maxWidth: "44rem" }}>
          {overview.space.description}
        </p>
      )}

      <nav className="tabs" aria-label="Space sections" style={{ marginBottom: "var(--space-5)" }}>
        {spaceNav(spaceId).map((item) => (
          <Link key={item.href} href={item.href} className="tab" aria-current={pathname === item.href ? "page" : undefined}>
            {item.label}
          </Link>
        ))}
      </nav>

      {overview && (
        <>
          <EditSpaceDialog open={showEdit} onClose={() => setShowEdit(false)} space={overview.space} />
          <ConfirmDialog
            open={showDelete}
            onClose={() => setShowDelete(false)}
            title="Delete this space?"
            description={
              hasProjects
                ? `This space still has ${overview.project_count} project${overview.project_count === 1 ? "" : "s"} in it. Move or delete ${overview.project_count === 1 ? "it" : "them"} first — AtlasAI won't delete a space that still has projects.`
                : "This can't be undone."
            }
            confirmLabel="Delete"
            onConfirm={async () => {
              try {
                await deleteSpace.mutateAsync(spaceId);
                toast({ title: "Space deleted", variant: "success" });
                router.push("/app/spaces");
              } catch (err) {
                toast({
                  title: "Couldn't delete space",
                  description: err instanceof ApiError ? String(err.detail) : undefined,
                  variant: "danger",
                });
              }
            }}
          />
        </>
      )}

      {children}
    </div>
  );
}
