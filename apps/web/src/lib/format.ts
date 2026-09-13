import { format, formatDistanceToNow, isValid, parseISO } from "date-fns";

function toDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = parseISO(value);
  return isValid(parsed) ? parsed : null;
}

export function formatRelativeTime(value: string | null | undefined): string {
  const date = toDate(value);
  if (!date) return "—";
  return formatDistanceToNow(date, { addSuffix: true });
}

export function formatDateTime(value: string | null | undefined): string {
  const date = toDate(value);
  if (!date) return "—";
  return format(date, "d MMM yyyy, h:mm a");
}

export function formatDate(value: string | null | undefined): string {
  const date = toDate(value);
  if (!date) return "—";
  return format(date, "d MMM yyyy");
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0]}${parts[parts.length - 1]![0]}`.toUpperCase();
}

export function isStale(value: string | null | undefined, thresholdHours = 72): boolean {
  const date = toDate(value);
  if (!date) return true;
  return Date.now() - date.getTime() > thresholdHours * 60 * 60 * 1000;
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
