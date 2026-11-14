"use client";
/** Recorded workflow timeline reconstructed from job start/end timestamps. */
import { useMemo, useState } from "react";
import type { WorkflowJob } from "@/data/schemas/presentationSchema";
import { formatSeconds } from "@/lib/format";

const stageColor: Record<WorkflowJob["stage"], string> = {
  simulation: "#FF6B35", dataset: "#FFB547", training: "#48D8FF", evaluation: "#35D6A0", inference: "#48D8FF", other: "#94A3B8",
};

export function GanttChart({ jobs, width, height, playhead }: { jobs: WorkflowJob[]; width: number; height: number; playhead: number /* 0..1 */ }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const timed = useMemo(() => jobs.filter((j) => j.start && j.end), [jobs]);
  const untimed = jobs.length - timed.length;
  const t0 = Math.min(...timed.map((j) => Date.parse(j.start!)));
  const t1 = Math.max(...timed.map((j) => Date.parse(j.end!)));
  const span = Math.max(1, t1 - t0);
  const labelWidth = 260;
  const plotWidth = width - labelWidth - 30;
  const rowHeight = Math.min(64, (height - 60) / Math.max(1, timed.length));
  const xOf = (iso: string) => labelWidth + ((Date.parse(iso) - t0) / span) * plotWidth;
  const rowOf = new Map(timed.map((j, k) => [j.id, k]));
  const ticks = 6;

  if (timed.length === 0) {
    return <div className="fontMono text-mute">No job timestamps recorded ({jobs.length} jobs without start/end).</div>;
  }

  const hoveredJob = timed.find((j) => j.id === hovered) ?? null;
  const playX = labelWidth + playhead * plotWidth;

  return (
    <div className="relative">
      <svg width={width} height={height} role="img" aria-label="Recorded workflow Gantt chart">
        {Array.from({ length: ticks + 1 }, (_, k) => {
          const x = labelWidth + (k / ticks) * plotWidth;
          return (
            <g key={k}>
              <line x1={x} y1={0} x2={x} y2={height - 34} stroke="#243042" />
              <text x={x} y={height - 10} textAnchor={k === ticks ? "end" : k === 0 ? "start" : "middle"} className="fontMono" fontSize={14} fill="#94A3B8">{k === 0 ? "start" : `+${formatSeconds(((k / ticks) * span) / 1000)}`}</text>
            </g>
          );
        })}
        {timed.map((job, k) =>
          job.dependsOn.map((dep) => {
            const from = timed.find((j) => j.id === dep);
            if (!from || !rowOf.has(dep)) return null;
            const x1 = xOf(from.end!);
            const y1 = rowOf.get(dep)! * rowHeight + rowHeight / 2 + 6;
            const x2 = xOf(job.start!);
            const y2 = k * rowHeight + rowHeight / 2 + 6;
            return <path key={`${dep}-${job.id}`} d={`M${x1},${y1} C${x1 + 30},${y1} ${x2 - 30},${y2} ${x2 - 4},${y2}`} stroke="#A3B8D9" strokeOpacity={0.45} strokeWidth={1.5} fill="none" markerEnd="url(#ganttArrow)" />;
          }),
        )}
        <defs>
          <marker id="ganttArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#A3B8D9" />
          </marker>
        </defs>
        {timed.map((job, k) => {
          const x = xOf(job.start!);
          const w = Math.max(4, xOf(job.end!) - x);
          const y = k * rowHeight + 6;
          const color = stageColor[job.stage];
          const revealed = Math.max(0, Math.min(w, playX - x));
          return (
            <g key={job.id} onMouseEnter={() => setHovered(job.id)} onMouseLeave={() => setHovered(null)} style={{ cursor: "default" }}>
              <text x={labelWidth - 16} y={y + rowHeight / 2 + 1} textAnchor="end" className="fontMono" fontSize={15} fill={hovered === job.id ? "#F3F6FA" : "#94A3B8"}>
                {job.name.length > 24 ? `${job.name.slice(0, 23)}…` : job.name}
              </text>
              <rect x={x} y={y + 4} width={w} height={rowHeight - 14} rx={6} fill={color} fillOpacity={0.14} stroke={color} strokeOpacity={0.5} />
              <rect x={x} y={y + 4} width={revealed} height={rowHeight - 14} rx={6} fill={color} fillOpacity={job.state === "failed" ? 0.35 : 0.8} />
              {job.node && w > 70 ? <text x={x + 10} y={y + rowHeight / 2 + 1} className="fontMono" fontSize={13} fill="#080B10" opacity={revealed > 60 ? 1 : 0}>{job.node}</text> : null}
              {job.state !== "completed" ? <text x={x + w + 8} y={y + rowHeight / 2 + 1} className="fontMono" fontSize={13} fill="#E53935">{job.state}</text> : null}
            </g>
          );
        })}
        <line x1={playX} y1={0} x2={playX} y2={height - 34} stroke="#F3F6FA" strokeOpacity={0.7} strokeWidth={1.5} />
      </svg>
      {hoveredJob ? (
        <div className="glassPanel fontMono pointer-events-none absolute right-0 top-0 w-[380px] rounded-xl p-4 text-[14px]">
          <div className="fontDisplay mb-1 text-[18px] text-ink">{hoveredJob.name}</div>
          <div className="text-mute">id: <span className="text-ink">{hoveredJob.id}</span></div>
          <div className="text-mute">state: <span className="text-ink">{hoveredJob.state}</span> · node: <span className="text-ink">{hoveredJob.node ?? "not recorded"}</span></div>
          <div className="text-mute">duration: <span className="text-ink">{formatSeconds((Date.parse(hoveredJob.end!) - Date.parse(hoveredJob.start!)) / 1000)}</span></div>
          {hoveredJob.resources ? <div className="text-mute">resources: <span className="text-ink">{hoveredJob.resources.cpu ?? "—"} CPU · {hoveredJob.resources.gpu ?? "—"} GPU · {hoveredJob.resources.memoryGb ?? "—"} GB</span></div> : null}
          {hoveredJob.dependsOn.length ? <div className="text-mute">after: <span className="text-ink">{hoveredJob.dependsOn.join(", ")}</span></div> : null}
          {hoveredJob.artifacts.length ? <div className="text-mute">artifacts: <span className="text-[#35D6A0]">{hoveredJob.artifacts.join(", ")}</span></div> : null}
        </div>
      ) : null}
      {untimed > 0 ? <div className="fontMono mt-1 text-[13px] text-mute">{untimed} job(s) without timestamps omitted from timeline.</div> : null}
    </div>
  );
}
