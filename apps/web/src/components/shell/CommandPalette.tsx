"use client";

import { FolderKanban, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import { useProjects } from "@/hooks/useProjects";
import { PRIMARY_NAV } from "@/lib/nav";
import { useUiStore } from "@/store/ui";

export function CommandPalette() {
  const open = useUiStore((s) => s.commandPaletteOpen);
  const setOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const router = useRouter();
  const { data: projects } = useProjects();

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, setOpen]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIndex(0);
    }
  }, [open]);

  const navMatches = useMemo(
    () => PRIMARY_NAV.filter((item) => item.label.toLowerCase().includes(query.toLowerCase())),
    [query],
  );
  const projectMatches = useMemo(
    () => (projects ?? []).filter((p) => p.name.toLowerCase().includes(query.toLowerCase())).slice(0, 6),
    [projects, query],
  );

  const flatResults = [
    ...navMatches.map((item) => ({ type: "nav" as const, href: item.href, label: item.label, icon: item.icon })),
    ...projectMatches.map((p) => ({ type: "project" as const, href: `/app/projects/${p.id}/overview`, label: p.name })),
  ];

  function go(href: string) {
    setOpen(false);
    router.push(href);
  }

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!open) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, flatResults.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        const item = flatResults[activeIndex];
        if (item) go(item.href);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, activeIndex, flatResults.length]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div className="command-palette-overlay" onMouseDown={() => setOpen(false)}>
      <div className="command-palette" onMouseDown={(e) => e.stopPropagation()}>
        <div className="command-palette__input-row">
          <Search size={18} color="var(--text-tertiary)" aria-hidden />
          <input
            autoFocus
            className="command-palette__input"
            placeholder="Search projects, findings, evidence…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Command palette search"
          />
          <kbd style={{ fontSize: "var(--font-size-2xs)", color: "var(--text-tertiary)" }}>Esc</kbd>
        </div>
        <div className="command-palette__results">
          {navMatches.length > 0 && (
            <>
              <p className="command-palette__group-label">Navigate</p>
              {navMatches.map((item) => {
                const flatIndex = flatResults.findIndex((r) => r.href === item.href && r.type === "nav");
                const Icon = item.icon;
                return (
                  <button
                    key={item.href}
                    type="button"
                    className="command-palette__item"
                    data-active={flatIndex === activeIndex}
                    onClick={() => go(item.href)}
                    onMouseEnter={() => setActiveIndex(flatIndex)}
                  >
                    <Icon size={16} aria-hidden /> {item.label}
                  </button>
                );
              })}
            </>
          )}
          {projectMatches.length > 0 && (
            <>
              <p className="command-palette__group-label">Projects</p>
              {projectMatches.map((p) => {
                const href = `/app/projects/${p.id}/overview`;
                const flatIndex = flatResults.findIndex((r) => r.href === href && r.type === "project");
                return (
                  <button
                    key={p.id}
                    type="button"
                    className="command-palette__item"
                    data-active={flatIndex === activeIndex}
                    onClick={() => go(href)}
                    onMouseEnter={() => setActiveIndex(flatIndex)}
                  >
                    <FolderKanban size={16} aria-hidden /> {p.name}
                  </button>
                );
              })}
            </>
          )}
          {flatResults.length === 0 && (
            <p style={{ padding: "var(--space-5)", textAlign: "center", color: "var(--text-tertiary)", fontSize: "var(--font-size-sm)" }}>
              No matches for &ldquo;{query}&rdquo;
            </p>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
