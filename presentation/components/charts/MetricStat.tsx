"use client";
/** Animated metric readout. Null renders as an em dash, never as zero. */
import { useCountUp } from "@/hooks/useCountUp";
import { missingValue } from "@/lib/format";

export function MetricStat({ label, value, format, active, reducedMotion, color = "#F3F6FA", size = "md", hint }: {
  label: string;
  value: number | null;
  format: (v: number) => string;
  active: boolean;
  reducedMotion: boolean;
  color?: string;
  size?: "sm" | "md" | "lg";
  hint?: string;
}) {
  const animated = useCountUp(value, active, 1200, reducedMotion);
  const fontSize = size === "lg" ? 76 : size === "md" ? 40 : 28;
  return (
    <div>
      <div className="fontMono text-[14px] uppercase tracking-[0.18em] text-mute">{label}</div>
      <div className="fontMono font-semibold tabular-nums leading-tight" style={{ fontSize, color: value === null ? "#5B6678" : color }}>
        {animated === null ? missingValue : format(animated)}
      </div>
      {hint ? <div className="text-[14px] text-mute">{hint}</div> : null}
    </div>
  );
}
