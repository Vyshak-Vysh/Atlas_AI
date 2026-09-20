"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";

interface DropdownMenuProps {
  trigger: ReactNode;
  children: ReactNode;
  align?: "left" | "right";
}

export function DropdownMenu({ trigger, children, align = "right" }: DropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-block" }}>
      <span onClick={() => setOpen((o) => !o)}>{trigger}</span>
      <AnimatePresence>
        {open && (
          <motion.div
            className="menu-popover"
            style={{
              position: "absolute",
              ...(align === "right" ? { right: 0 } : { left: 0 }),
              top: "calc(100% + 0.4rem)",
              transformOrigin: align === "right" ? "top right" : "top left",
            }}
            initial={{ opacity: 0, scale: 0.95, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -4 }}
            transition={{ duration: 0.12, ease: [0.2, 0.8, 0.2, 1] }}
            onClick={() => setOpen(false)}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function MenuItem({
  children,
  onClick,
  danger,
  icon,
  href,
}: {
  children: ReactNode;
  onClick?: () => void;
  danger?: boolean;
  icon?: ReactNode;
  href?: string;
}) {
  const className = danger ? "menu-item menu-item--danger" : "menu-item";
  if (href) {
    return (
      <a href={href} className={className}>
        {icon}
        {children}
      </a>
    );
  }
  return (
    <button type="button" className={className} onClick={onClick}>
      {icon}
      {children}
    </button>
  );
}

export function MenuSeparator() {
  return <div className="menu-separator" />;
}
