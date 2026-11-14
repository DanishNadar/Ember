"use client";
/** Animates a number from 0 to target when `active` becomes true. Null stays null. */
import { useEffect, useState } from "react";

export function useCountUp(target: number | null, active: boolean, durationMs = 1400, reducedMotion = false): number | null {
  const [value, setValue] = useState<number | null>(target === null ? null : reducedMotion ? target : 0);

  useEffect(() => {
    if (target === null) {
      setValue(null);
      return;
    }
    if (!active) {
      setValue(reducedMotion ? target : 0);
      return;
    }
    if (reducedMotion) {
      setValue(target);
      return;
    }
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(target * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, active, durationMs, reducedMotion]);

  return value;
}
