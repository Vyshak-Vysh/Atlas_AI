"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * Minimal hover/focus tooltip — there was no tooltip primitive anywhere in
 * the app, so every icon-only button (Topbar's search/notifications/theme/
 * user-menu triggers, and similar icon buttons added since) relied solely
 * on an `aria-label` with no VISIBLE hover affordance for sighted users.
 * Wrap a single trigger element; shown after a short delay on hover/focus,
 * hidden immediately on mousedown so it never overlaps a menu that opens
 * from the same trigger.
 */
export function Tooltip({ label, children, side = "bottom" }: { label: string; children: ReactNode; side?: "top" | "bottom" }) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  }, []);

  function show() {
    timeoutRef.current = setTimeout(() => setVisible(true), 350);
  }
  function hide() {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  }

  return (
    <span
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      onMouseDown={hide}
    >
      {children}
      <AnimatePresence>
        {visible && (
          <motion.span
            role="tooltip"
            className="tooltip"
            data-side={side}
            initial={{ opacity: 0, y: side === "bottom" ? -3 : 3 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: side === "bottom" ? -3 : 3 }}
            transition={{ duration: 0.1 }}
          >
            {label}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
