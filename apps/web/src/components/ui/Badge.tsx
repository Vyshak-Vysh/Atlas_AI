import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import type { StatusDisplay } from "@/lib/status";

type Variant = "success" | "warning" | "danger" | "info" | "discovery" | "neutral";

export function Badge({ variant = "neutral", children }: { variant?: Variant; children: ReactNode }) {
  return <span className={cn("badge", `badge--${variant}`)}>{children}</span>;
}

export function StatusBadge({ status }: { status: StatusDisplay }) {
  return <span className={cn("badge", "status-badge", status.className)}>{status.label}</span>;
}

export function AiTag() {
  return <span className="ai-tag">AI-generated</span>;
}

export function HumanTag() {
  return <span className="human-tag">Human-confirmed</span>;
}
