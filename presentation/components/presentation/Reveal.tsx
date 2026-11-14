"use client";
/** Fades/slides content in when `show` becomes true. Instant under reduced motion. */
import { motion } from "framer-motion";
import type { ReactNode } from "react";

export function Reveal({ show, children, delay = 0, y = 20, className = "", reducedMotion = false }: {
  show: boolean;
  children: ReactNode;
  delay?: number;
  y?: number;
  className?: string;
  reducedMotion?: boolean;
}) {
  return (
    <motion.div
      className={className}
      initial={false}
      animate={{ opacity: show ? 1 : 0, y: show ? 0 : y }}
      transition={reducedMotion ? { duration: 0 } : { duration: 0.7, delay: show ? delay : 0, ease: [0.2, 0.7, 0.2, 1] }}
      style={{ pointerEvents: show ? "auto" : "none" }}
    >
      {children}
    </motion.div>
  );
}
