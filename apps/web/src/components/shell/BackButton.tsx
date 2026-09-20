"use client";

import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

import { useBreadcrumbTrail } from "./Breadcrumbs";

/**
 * Explicit, always-visible "go up one level" affordance — the breadcrumb
 * trail is clickable but small and easy to miss, and this app is often run
 * full-screen without visible browser chrome, so users have no obvious way
 * back after drilling into a task/finding/investigation detail page. Always
 * navigates to the parent breadcrumb (not `router.back()`), so it works the
 * same after a hard refresh or a link opened directly, not just mid-session.
 */
export function BackButton() {
  const router = useRouter();
  const crumbs = useBreadcrumbTrail();

  if (crumbs.length < 2) return null;

  const parent = crumbs[crumbs.length - 2]!;

  return (
    <button
      type="button"
      className="topbar-icon-btn"
      onClick={() => router.push(parent.href)}
      aria-label={`Back to ${parent.label}`}
      title={`Back to ${parent.label}`}
    >
      <ArrowLeft size={18} aria-hidden />
    </button>
  );
}
