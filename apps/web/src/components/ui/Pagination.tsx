"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect } from "react";

import { Button } from "./Button";

/**
 * Page-through control for a list already loaded into memory. There was no
 * pagination primitive anywhere in the app — Findings, Approvals, Team, and
 * Audit log all rendered their full result set into one ever-growing table,
 * with no page-size control, so a workspace with real data volume just got
 * taller and taller. Pairs with `usePagination` below, which slices an
 * already-fetched array; it does not itself page a backend request.
 */
export function Pagination({
  page,
  pageCount,
  onPageChange,
  totalItems,
  pageSize,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  totalItems: number;
  pageSize: number;
}) {
  if (pageCount <= 1) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, totalItems);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "var(--space-4)",
        marginTop: "var(--space-4)",
        paddingTop: "var(--space-4)",
        borderTop: "1px solid var(--border-subtle)",
      }}
    >
      <p style={{ margin: 0, fontSize: "var(--font-size-sm)", color: "var(--text-tertiary)" }}>
        {start}–{end} of {totalItems}
      </p>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
        <Button variant="secondary" size="small" onClick={() => onPageChange(page - 1)} disabled={page <= 1} aria-label="Previous page">
          <ChevronLeft size={14} aria-hidden />
        </Button>
        <span style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", minWidth: "5rem", textAlign: "center" }}>
          Page {page} of {pageCount}
        </span>
        <Button variant="secondary" size="small" onClick={() => onPageChange(page + 1)} disabled={page >= pageCount} aria-label="Next page">
          <ChevronRight size={14} aria-hidden />
        </Button>
      </div>
    </div>
  );
}

/** Slices `rows` to the current page and clamps `page` back in range
 * whenever the underlying data shrinks (e.g. a filter is applied) so the
 * view never gets stuck showing an empty page 4 of 2. */
export function usePagination<T>(rows: T[], page: number, setPage: (page: number) => void, pageSize = 25) {
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const clampedPage = Math.min(page, pageCount);

  useEffect(() => {
    if (clampedPage !== page) setPage(clampedPage);
  }, [clampedPage, page, setPage]);

  const start = (clampedPage - 1) * pageSize;
  return {
    pageRows: rows.slice(start, start + pageSize),
    page: clampedPage,
    pageCount,
  };
}
