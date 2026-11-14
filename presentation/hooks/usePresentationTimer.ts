"use client";
/** Simple start/pause/reset stopwatch for the talk. */
import { useCallback, useEffect, useRef, useState } from "react";

export function usePresentationTimer() {
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);
  const startedAt = useRef<number | null>(null);
  const banked = useRef(0);

  useEffect(() => {
    if (!running) return;
    startedAt.current = Date.now();
    const id = window.setInterval(() => {
      setElapsed(banked.current + (Date.now() - (startedAt.current ?? Date.now())) / 1000);
    }, 250);
    return () => {
      banked.current += (Date.now() - (startedAt.current ?? Date.now())) / 1000;
      startedAt.current = null;
      window.clearInterval(id);
    };
  }, [running]);

  const toggle = useCallback(() => setRunning((r) => !r), []);
  const start = useCallback(() => setRunning(true), []);
  const reset = useCallback(() => {
    banked.current = 0;
    startedAt.current = running ? Date.now() : null;
    setElapsed(0);
  }, [running]);

  return { elapsed, running, toggle, start, reset };
}
