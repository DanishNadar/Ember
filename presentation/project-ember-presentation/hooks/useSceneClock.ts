"use client";
/**
 * Scene time in seconds. Live slides animate from 0 when they become active; previews
 * and reduced-motion mode jump straight to the composed end state (`settledTime`).
 */
import { useAnimationClock } from "./useAnimationClock";

export function useSceneClock({ isActive, isPreview, reducedMotion, settledTime, resetKey = 0, maxFps = 60 }: {
  isActive: boolean;
  isPreview?: boolean;
  reducedMotion: boolean;
  settledTime: number;
  resetKey?: unknown;
  maxFps?: number;
}): number {
  const animate = isActive && !isPreview && !reducedMotion;
  const elapsed = useAnimationClock(animate, `${String(resetKey)}:${isActive}`, maxFps);
  return animate ? elapsed : settledTime;
}
