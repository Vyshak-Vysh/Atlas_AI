"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemePreference = "light" | "dark" | "system";

interface UiState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  mobileNavOpen: boolean;
  setMobileNavOpen: (open: boolean) => void;
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  theme: ThemePreference;
  setTheme: (theme: ThemePreference) => void;
  /** Which sidebar tree rows (Spaces/Projects) are expanded, keyed by
   * "space:<id>" / "project:<id>" / "ungrouped". Plain string[] (not a
   * Set) because zustand's `persist` JSON-serializes state as-is. */
  expandedNavIds: string[];
  toggleNavExpanded: (id: string) => void;
  expandNavIds: (ids: string[]) => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set, get) => ({
      sidebarCollapsed: false,
      toggleSidebar: () => set({ sidebarCollapsed: !get().sidebarCollapsed }),
      mobileNavOpen: false,
      setMobileNavOpen: (open) => set({ mobileNavOpen: open }),
      commandPaletteOpen: false,
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      theme: "system",
      setTheme: (theme) => set({ theme }),
      expandedNavIds: [],
      toggleNavExpanded: (id) =>
        set({
          expandedNavIds: get().expandedNavIds.includes(id)
            ? get().expandedNavIds.filter((existing) => existing !== id)
            : [...get().expandedNavIds, id],
        }),
      expandNavIds: (ids) => {
        const missing = ids.filter((id) => !get().expandedNavIds.includes(id));
        if (missing.length > 0) set({ expandedNavIds: [...get().expandedNavIds, ...missing] });
      },
    }),
    {
      name: "atlasai.ui",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        expandedNavIds: state.expandedNavIds,
      }),
    },
  ),
);
