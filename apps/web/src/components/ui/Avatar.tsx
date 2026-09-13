import { initials } from "@/lib/format";

export function Avatar({ name, size = 32 }: { name: string; size?: number }) {
  return (
    <span
      className="avatar"
      style={{ width: size, height: size, fontSize: size <= 24 ? "0.6rem" : undefined }}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}
