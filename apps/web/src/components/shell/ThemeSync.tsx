"use client";

import { useEffect } from "react";

import { useUiStore } from "@/store/ui";

/** Keeps `<html data-theme>` in sync with the zustand-persisted preference
 * whenever it changes at runtime (the inline ThemeScript only handles the
 * very first paint). */
export function ThemeSync() {
  const theme = useUiStore((s) => s.theme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
  }, [theme]);

  return null;
}
