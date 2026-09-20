"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment } from "react";

import { useProjectOverview } from "@/hooks/useProjects";
import { useSpaceOverview } from "@/hooks/useSpaces";

const LABELS: Record<string, string> = {
  app: "AtlasAI",
  overview: "Overview",
  projects: "Projects",
  new: "New project",
  evidence: "Evidence",
  findings: "Findings",
  approvals: "Approvals",
  reports: "Reports",
  connectors: "Connectors",
  team: "Team",
  audit: "Audit log",
  settings: "Settings",
  requirements: "Tasks",
  "project-space": "My Work",
  spaces: "Spaces",
  investigations: "Investigations",
  activity: "Activity",
  organization: "Organization",
  members: "Members",
  roles: "Roles",
  security: "Security",
  billing: "Billing",
  profile: "Your profile",
};

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Singular labels for a UUID segment that follows this parent segment —
// e.g. .../investigations/<runId> -> "Investigation", not the project name.
const ENTITY_LABELS: Record<string, string> = {
  investigations: "Investigation",
  findings: "Finding",
  approvals: "Approval",
  requirements: "Task",
};

export interface Crumb {
  href: string;
  label: string;
}

/** Shared by <Breadcrumbs> and the Topbar's back button, so both agree on
 * what the "parent" of the current page is. */
export function useBreadcrumbTrail(): Crumb[] {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  const projectsIndex = segments.indexOf("projects");
  const projectIdIndex = projectsIndex >= 0 ? projectsIndex + 1 : -1;
  const projectId =
    projectIdIndex > 0 && segments[projectIdIndex] && UUID_RE.test(segments[projectIdIndex]!)
      ? segments[projectIdIndex]
      : undefined;
  const { data: overview } = useProjectOverview(projectId);

  const spacesIndex = segments.indexOf("spaces");
  const spaceIdIndex = spacesIndex >= 0 ? spacesIndex + 1 : -1;
  const spaceId =
    spaceIdIndex > 0 && segments[spaceIdIndex] && UUID_RE.test(segments[spaceIdIndex]!)
      ? segments[spaceIdIndex]
      : undefined;
  const { data: spaceOverview } = useSpaceOverview(spaceId);

  let href = "";
  return segments
    .filter((s) => s !== "app")
    .map((segment, i) => {
      href += `/${segment}`;
      const originalIndex = i + 1; // account for the filtered-out leading "app" segment
      const isProjectIdSegment = originalIndex === projectIdIndex;
      const isSpaceIdSegment = originalIndex === spaceIdIndex;
      const isUuid = UUID_RE.test(segment);

      let label: string;
      if (isProjectIdSegment) {
        label = overview?.project.name ?? "Project";
      } else if (isSpaceIdSegment) {
        label = spaceOverview?.space.name ?? "Space";
      } else if (isUuid) {
        const parent = segments[originalIndex - 1];
        label = ENTITY_LABELS[parent ?? ""] ?? "Detail";
      } else {
        label = LABELS[segment] ?? segment;
      }
      return { href: `/app${href}`, label };
    });
}

export function Breadcrumbs() {
  const crumbs = useBreadcrumbTrail();

  if (crumbs.length === 0) return <span />;

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      {crumbs.map((crumb, i) => (
        <Fragment key={crumb.href}>
          {i > 0 && <span aria-hidden>/</span>}
          {i === crumbs.length - 1 ? (
            <span style={{ color: "var(--text-primary)", fontWeight: "var(--font-weight-medium)" }}>{crumb.label}</span>
          ) : (
            <Link href={crumb.href}>{crumb.label}</Link>
          )}
        </Fragment>
      ))}
    </nav>
  );
}
