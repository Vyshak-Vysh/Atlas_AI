import type { CSSProperties } from "react";

import { cn } from "@/lib/cn";

export function Skeleton({ className, style }: { className?: string; style?: CSSProperties }) {
  return <div className={cn("skeleton", className)} style={style} aria-hidden />;
}

export function SkeletonLines({ count = 3 }: { count?: number }) {
  return (
    <div style={{ display: "grid", gap: "var(--space-2)" }}>
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} style={{ height: "0.85rem", width: i === count - 1 ? "60%" : "100%" }} />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="card">
      <div className="card__body">
        <Skeleton style={{ height: "1.25rem", width: "40%", marginBottom: "var(--space-4)" }} />
        <SkeletonLines count={3} />
      </div>
    </div>
  );
}

export function SkeletonMetricGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="metric-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="metric-card">
          <Skeleton style={{ height: "0.85rem", width: "60%" }} />
          <Skeleton style={{ height: "1.75rem", width: "40%", marginTop: "var(--space-3)" }} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="table-wrapper">
      <div style={{ padding: "var(--space-4)", display: "grid", gap: "var(--space-3)" }}>
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} style={{ height: "1.5rem", width: "100%" }} />
        ))}
      </div>
    </div>
  );
}
