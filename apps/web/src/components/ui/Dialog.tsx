"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

const EASE_OUT: [number, number, number, number] = [0.2, 0.8, 0.2, 1];
const EASE_SPRING: [number, number, number, number] = [0.34, 1.56, 0.64, 1];

export function Dialog({ open, onClose, title, children, footer, wide }: DialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    document.body.style.overflow = "hidden";

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
      previouslyFocused.current?.focus?.();
    };
  }, [open, onClose]);

  if (typeof document === "undefined") return null;

  // The portal itself renders unconditionally once mounted; AnimatePresence
  // needs to see the `open`-guarded child unmount (not the whole tree
  // early-return) to know it should play an exit transition first, instead
  // of the dialog just vanishing the instant `open` flips to false.
  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.16, ease: EASE_OUT }}
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) onClose();
          }}
        >
          <motion.div
            ref={dialogRef}
            className={wide ? "dialog dialog--wide" : "dialog"}
            role="dialog"
            aria-modal="true"
            aria-label={typeof title === "string" ? title : undefined}
            tabIndex={-1}
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 4 }}
            transition={{ duration: 0.18, ease: EASE_SPRING }}
          >
            <div className="dialog__header">
              <h2 className="dialog__title">{title}</h2>
              <button type="button" className="close-btn" onClick={onClose} aria-label="Close dialog">
                <X size={18} aria-hidden />
              </button>
            </div>
            <div className="dialog__body">{children}</div>
            {footer && <div className="dialog__footer">{footer}</div>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
