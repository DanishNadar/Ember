"use client";
/** Letterboxed 16:9 stage. Slides are authored at 1920×1080 and scaled uniformly. */
import type { ReactNode } from "react";
import { useStageScale } from "@/hooks/useStageScale";
import { stageHeight, stageWidth } from "@/lib/theme";

export function Stage({ children, className = "" }: { children: ReactNode; className?: string }) {
  const { containerRef, scale } = useStageScale<HTMLDivElement>();
  return (
    <div ref={containerRef} className={`relative h-full w-full overflow-hidden ${className}`}>
      <div
        className="absolute left-1/2 top-1/2 overflow-hidden bg-void"
        style={{
          width: stageWidth,
          height: stageHeight,
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
