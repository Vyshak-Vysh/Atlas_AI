import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  actions,
}: {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-state__icon">
        <Icon size={22} aria-hidden />
      </div>
      <p className="empty-state__title">{title}</p>
      {description && <p style={{ maxWidth: "32rem" }}>{description}</p>}
      {actions && <div className="empty-state__actions">{actions}</div>}
    </div>
  );
}
