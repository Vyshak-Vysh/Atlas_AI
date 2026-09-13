import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export function MetricCard({
  label,
  value,
  meta,
  href,
  icon: Icon,
}: {
  label: string;
  value: ReactNode;
  meta?: ReactNode;
  href?: string;
  icon?: LucideIcon;
}) {
  const content = (
    <>
      <div className="metric-card__label">
        <span>{label}</span>
        {Icon && <Icon size={15} aria-hidden style={{ opacity: 0.6 }} />}
      </div>
      <div className="metric-card__value">{value}</div>
      {meta && <div className="metric-card__meta">{meta}</div>}
    </>
  );

  if (href) {
    return (
      <Link href={href} className="metric-card">
        {content}
      </Link>
    );
  }
  return <div className="metric-card">{content}</div>;
}
