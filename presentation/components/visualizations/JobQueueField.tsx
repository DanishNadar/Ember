"use client";
/**
 * Normalized, conceptual job-queue animation: scenario requests arrive at an accelerating
 * rate while a fixed worker pool drains them. Units are abstract; no timings are claimed.
 */
import { useMemo } from "react";

interface ScheduledJob {
  arrival: number;
  start: number;
  end: number;
  worker: number;
}

const workerCount = 4;
const jobDuration = 1.6; // abstract time units
const maxJobs = 420;

function buildSchedule(): ScheduledJob[] {
  const jobs: ScheduledJob[] = [];
  const freeAt = new Array(workerCount).fill(0);
  for (let k = 1; k <= maxJobs; k++) {
    // Cumulative arrivals A(t) = 1.2 t + 1.2 t^2  →  solve for t.
    const arrival = (-1.2 + Math.sqrt(1.44 + 4 * 1.2 * k)) / (2 * 1.2);
    let worker = 0;
    for (let w = 1; w < workerCount; w++) if (freeAt[w] < freeAt[worker]) worker = w;
    const start = Math.max(arrival, freeAt[worker]);
    const end = start + jobDuration;
    freeAt[worker] = end;
    jobs.push({ arrival, start, end, worker });
  }
  return jobs;
}

export function JobQueueField({ time, width, height }: { time: number; width: number; height: number }) {
  const schedule = useMemo(buildSchedule, []);
  const arrived = schedule.filter((j) => j.arrival <= time);
  const waiting = arrived.filter((j) => j.start > time);
  const running = arrived.filter((j) => j.start <= time && j.end > time);
  const done = arrived.filter((j) => j.end <= time);

  const cell = 32;
  const gap = 8;
  const queueCols = 12;
  const queueX = 40;
  const queueY = 90;
  const laneX = queueX + queueCols * (cell + gap) + 80;
  const laneWidth = 420;
  const laneHeight = 70;
  const doneX = laneX + laneWidth + 90;

  return (
    <svg width={width} height={height} role="img" aria-label="Conceptual animation of simulation jobs queuing for a fixed worker pool">
      <text x={queueX} y={50} className="fontMono" fontSize={18} fill="#94A3B8" letterSpacing="3">SCENARIO REQUESTS · WAITING</text>
      <text x={laneX} y={50} className="fontMono" fontSize={18} fill="#94A3B8" letterSpacing="3">FIXED SIMULATION WORKERS</text>
      <text x={doneX} y={50} className="fontMono" fontSize={18} fill="#94A3B8" letterSpacing="3">COMPLETED</text>

      {waiting.slice(0, queueCols * 11).map((job, k) => {
        const col = k % queueCols;
        const row = Math.floor(k / queueCols);
        const age = Math.min(1, (time - job.arrival) / 0.4);
        return (
          <rect
            key={job.arrival}
            x={queueX + col * (cell + gap)}
            y={queueY + row * (cell + gap) - (1 - age) * 30}
            width={cell}
            height={cell}
            rx={5}
            fill="#FF6B35"
            fillOpacity={0.2 + 0.55 * age}
            stroke="#FF6B35"
            strokeOpacity={0.6}
          />
        );
      })}
      {waiting.length > queueCols * 11 ? (
        <text x={queueX} y={queueY + 11 * (cell + gap) + 30} className="fontMono" fontSize={18} fill="#FF6B35">+{waiting.length - queueCols * 11} more waiting</text>
      ) : null}

      {Array.from({ length: workerCount }, (_, w) => {
        const job = running.find((j) => j.worker === w);
        const progress = job ? (time - job.start) / jobDuration : 0;
        const y = queueY + w * (laneHeight + 26);
        return (
          <g key={w}>
            <rect x={laneX} y={y} width={laneWidth} height={laneHeight} rx={12} fill="#111722" stroke="#243042" />
            <text x={laneX + 18} y={y + 28} className="fontMono" fontSize={15} fill="#94A3B8">worker {w + 1}</text>
            <rect x={laneX + 18} y={y + 40} width={laneWidth - 36} height={12} rx={6} fill="#1A2230" />
            <rect x={laneX + 18} y={y + 40} width={(laneWidth - 36) * progress} height={12} rx={6} fill="#FF6B35" />
            {job ? <circle cx={laneX + laneWidth - 26} cy={y + 24} r={6} fill="#FFB547" className="slowPulse" /> : null}
          </g>
        );
      })}

      {done.slice(-120).map((job, k) => {
        const col = k % 10;
        const row = Math.floor(k / 10);
        return <rect key={job.end} x={doneX + col * 18} y={queueY + row * 18} width={14} height={14} rx={3} fill="#94A3B8" fillOpacity={0.45} />;
      })}

      <g className="fontMono">
        <text x={queueX} y={height - 10} fontSize={22} fill="#F3F6FA">requested <tspan fill="#FF6B35" fontWeight={600}>{arrived.length}</tspan></text>
        <text x={laneX} y={height - 10} fontSize={22} fill="#F3F6FA">completed <tspan fill="#94A3B8" fontWeight={600}>{done.length}</tspan></text>
        <text x={doneX} y={height - 10} fontSize={22} fill="#F3F6FA">waiting <tspan fill="#E53935" fontWeight={600}>{waiting.length}</tspan></text>
      </g>
    </svg>
  );
}
