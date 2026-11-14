"use client";
/**
 * Slide stage. Slides are authored at 1920×1080 and scaled uniformly.
 * With `fill`, the canvas grows along the spare axis to cover the whole container.
 */
import type { ReactNode } from "react";
import { useStageScale } from "@/hooks/useStageScale";

export function Stage({ children, className = "", fill = false }: { children: ReactNode; className?: string; fill?: boolean }) {
  const { containerRef, scale, width, height } = useStageScale<HTMLDivElement>(fill);
  return (
    <div ref={containerRef} className={`relative h-full w-full overflow-hidden ${className}`}>
      <div
        className="absolute left-1/2 top-1/2 overflow-hidden bg-void"
        style={{
          width,
          height,
          transform: `translate(-50%, -50%) scale(${scale})`,
          transformOrigin: "center center",
          opacity: scale > 0 ? 1 : 0,
        }}
      >
        {children}
      </div>
    </div>
  );
}
