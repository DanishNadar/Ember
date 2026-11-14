"use client";
/** Histogram of measured per-scenario inference latencies (ms) with p50/p95 markers. */
import { useMemo } from "react";

function quantile(sorted: number[], q: number) {
  const pos = (sorted.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

export function LatencyHistogram({ samples, width, height }: { samples: number[]; width: number; height: number }) {
  const { bins, lo, hi, p50, p95 } = useMemo(() => {
    const sorted = [...samples].sort((a, b) => a - b);
    const lo = sorted[0];
    const hi = sorted[sorted.length - 1];
    const count = 24;
    const bins = new Array(count).fill(0);
    const span = hi - lo || 1;
    for (const s of sorted) bins[Math.min(count - 1, Math.floor(((s - lo) / span) * count))]++;
    return { bins, lo, hi, p50: quantile(sorted, 0.5), p95: quantile(sorted, 0.95) };
  }, [samples]);

  const maxBin = Math.max(...bins);
  const plotH = height - 28;
  const barW = width / bins.length;
  const xOf = (v: number) => ((v - lo) / (hi - lo || 1)) * width;

  return (
    <svg width={width} height={height} role="img" aria-label="Inference latency distribution">
      {bins.map((b, k) => (
        <rect key={k} x={k * barW + 1} y={plotH - (b / maxBin) * plotH} width={barW - 2} height={(b / maxBin) * plotH} rx={2} fill="#48D8FF" fillOpacity={0.7} />
      ))}
      {[["p50", p50], ["p95", p95]].map(([label, v]) => (
        <g key={label as string}>
          <line x1={xOf(v as number)} y1={0} x2={xOf(v as number)} y2={plotH} stroke="#F3F6FA" strokeDasharray="3 4" />
          <text x={xOf(v as number) + 4} y={12} className="fontMono" fontSize={12} fill="#F3F6FA">{label} {(v as number).toFixed(2)} ms</text>
        </g>
      ))}
      <text x={0} y={height - 6} className="fontMono" fontSize={12} fill="#94A3B8">{lo.toFixed(2)} ms</text>
      <text x={width} y={height - 6} textAnchor="end" className="fontMono" fontSize={12} fill="#94A3B8">{hi.toFixed(2)} ms · n={samples.length}</text>
    </svg>
  );
}
