"use client";
/**
 * requestAnimationFrame clock that only runs while `running` is true.
 * Returns elapsed seconds since the clock (re)started. Deterministic visuals derive
 * everything from this elapsed time, so replays look identical.
 */
import { useEffect, useRef, useState } from "react";

export function useAnimationClock(running: boolean, resetKey: unknown = 0, maxFps = 60): number {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);
  const offsetRef = useRef(0);

  useEffect(() => {
    startRef.current = null;
    offsetRef.current = 0;
    setElapsed(0);
  }, [resetKey]);

  useEffect(() => {
    if (!running) {
      startRef.current = null;
      return;
    }
    let frame = 0;
    let lastPaint = 0;
    const minInterval = 1000 / maxFps;
    const tick = (now: number) => {
      if (startRef.current === null) startRef.current = now - offsetRef.current * 1000;
      if (now - lastPaint >= minInterval) {
        lastPaint = now;
        const seconds = (now - startRef.current) / 1000;
        offsetRef.current = seconds;
        setElapsed(seconds);
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [running, maxFps]);

  return elapsed;
}
