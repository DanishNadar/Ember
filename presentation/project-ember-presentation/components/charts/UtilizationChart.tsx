"use client";
/** Recorded GPU/CPU utilization over time, one small panel per node (no dual axes). */
import { useMemo, useState } from "react";

type Sample = { t: number; node: string; gpuPercent: number | null; cpuPercent: number | null };

export function UtilizationChart({ samples, width }: { samples: Sample[]; width: number }) {
  const nodes = useMemo(() => Array.from(new Set(samples.map((s) => s.node))), [samples]);
  const tMax = Math.max(...samples.map((s) => s.t), 1);
  const panelH = 110;
  const [hover, setHover] = useState<{ node: string; sample: Sample } | null>(null);

  const series = (node: string, key: "gpuPercent" | "cpuPercent") =>
    samples.filter((s) => s.node === node && s[key] !== null).map((s) => `${(s.t / tMax) * width},${panelH - ((s[key] as number) / 100) * panelH}`).join(" ");

  return (
    <div className="space-y-4">
      <div className="fontMono flex gap-5 text-[13px] text-mute">
        <span className="flex items-center gap-2"><span className="inline-block h-[2px] w-5 bg-[#48D8FF]" /> GPU %</span>
        <span className="flex items-center gap-2"><span className="inline-block h-[2px] w-5 bg-[#FF6B35]" /> CPU %</span>
        {hover ? <span className="text-ink">{hover.node} · t={hover.sample.t}s · GPU {hover.sample.gpuPercent ?? "—"}% · CPU {hover.sample.cpuPercent ?? "—"}%</span> : null}
      </div>
      {nodes.map((node) => (
        <div key={node}>
          <div className="fontMono mb-1 text-[13px] text-ink">{node}</div>
          <svg width={width} height={panelH} className="overflow-visible" onMouseLeave={() => setHover(null)}>
            <rect width={width} height={panelH} fill="#1A0F0C" rx={6} />
            {[25, 50, 75].map((g) => <line key={g} x1={0} x2={width} y1={panelH - (g / 100) * panelH} y2={panelH - (g / 100) * panelH} stroke="#3A2018" />)}
            <polyline points={series(node, "gpuPercent")} fill="none" stroke="#48D8FF" strokeWidth={2} />
            <polyline points={series(node, "cpuPercent")} fill="none" stroke="#FF6B35" strokeWidth={2} />
            {samples.filter((s) => s.node === node).map((s) => (
              <rect key={s.t} x={(s.t / tMax) * width - 6} y={0} width={12} height={panelH} fill="transparent" onMouseEnter={() => setHover({ node, sample: s })} />
            ))}
          </svg>
        </div>
      ))}
    </div>
  );
}
