"use client";
import { GitBranch, Cpu, Workflow, Package, RefreshCw } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { AwaitingResults } from "@/components/presentation/AwaitingResults";
import { GanttChart } from "@/components/charts/GanttChart";
import { useSceneClock } from "@/hooks/useSceneClock";
import { FuzzballLogo } from "@/components/visualizations/BrandMarks";
import { fuzzballGreen } from "@/lib/ecosystem";
import type { SlideProps } from "./slideTypes";

const contributions = [
  { Icon: RefreshCw, label: "Reproducible orchestration" },
  { Icon: GitBranch, label: "Dependency management" },
  { Icon: Cpu, label: "Resource-aware scheduling" },
  { Icon: Workflow, label: "Multi-stage execution" },
  { Icon: Package, label: "Artifact handling" },
];

const plannedDag = [
  { id: "sim", label: "simulate", x: 40, y: 40, color: "#FF6B35" },
  { id: "data", label: "build dataset", x: 300, y: 40, color: "#FFB547" },
  { id: "train", label: "train", x: 560, y: 40, color: "#48D8FF" },
  { id: "eval", label: "evaluate", x: 820, y: 40, color: "#35D6A0" },
  { id: "simMore", label: "simulate (cont.)", x: 300, y: 150, color: "#FF6B35" },
];
const dagEdges: Array<[string, string]> = [["sim", "data"], ["data", "train"], ["train", "eval"], ["sim", "simMore"], ["simMore", "eval"]];

function PlannedDag() {
  const find = (id: string) => plannedDag.find((n) => n.id === id)!;
  return (
    <svg width={1040} height={220} role="img" aria-label="Planned workflow dependency graph">
      {dagEdges.map(([a, b]) => {
        const A = find(a);
        const B = find(b);
        const d = B.y > A.y
          ? `M${A.x + 95},${A.y + 56} C${A.x + 95},${B.y + 28} ${B.x - 60},${B.y + 28} ${B.x},${B.y + 28}`
          : B.y < A.y
            ? `M${A.x + 190},${A.y + 28} C${B.x + 95},${A.y + 28} ${B.x + 95},${B.y + 80} ${B.x + 95},${B.y + 56}`
            : `M${A.x + 190},${A.y + 28} L${B.x},${B.y + 28}`;
        return <path key={`${a}${b}`} d={d} stroke="#A3B8D9" strokeOpacity={0.5} strokeWidth={2} fill="none" className="flowDash" />;
      })}
      {plannedDag.map((n) => (
        <g key={n.id}>
          <rect x={n.x} y={n.y} width={190} height={56} rx={12} fill="#1A0F0C" stroke={n.color} strokeOpacity={0.7} />
          <text x={n.x + 95} y={n.y + 34} textAnchor="middle" className="fontMono" fontSize={17} fill="#F3F6FA">{n.label}</text>
        </g>
      ))}
    </svg>
  );
}

export function Slide10Fuzzball({ isActive, isPreview, reducedMotion, data }: SlideProps) {
  const workflow = data.snapshot.workflow;
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 100, maxFps: 30 });
  const playhead = Math.min(1, time / 6);

  return (
    <SlideFrame
      sceneNumber={10}
      kicker="Fuzzball orchestration"
      headline={<>Computation, <span style={{ color: fuzzballGreen }}>coordinated.</span></>}
      accent={fuzzballGreen}
      aside={<FuzzballLogo height={104} />}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full flex-col gap-6">
        <div className="glassPanel min-h-0 flex-1 rounded-2xl p-6">
          {workflow ? (
            <>
              <div className="mb-3 flex items-center gap-4">
                <span className="fontMono text-[18px] text-ink">workflow {workflow.workflowId}</span>
                <span className="fontMono rounded-full border border-white/15 px-3 py-0.5 text-[14px] text-mute">RECORDED PLAYBACK · not live</span>
                {workflow.recordedAt ? <span className="fontMono text-[14px] text-mute">recorded {new Date(workflow.recordedAt).toLocaleString()}</span> : null}
                <span className="ml-auto"><EvidenceBadge kind={data.evidenceFor("workflow")} isFixture={data.isFixture} detail={workflow.source.path} /></span>
              </div>
              <GanttChart jobs={workflow.jobs} width={1660} height={Math.min(560, workflow.jobs.length * 64 + 60)} playhead={playhead} />
            </>
          ) : (
            <div className="flex h-full gap-8">
              <div className="flex flex-col justify-center">
                <div className="fontMono mb-3 text-[14px] uppercase tracking-[0.2em] text-mute">Planned dependency graph</div>
                <PlannedDag />
                <div className="mt-3"><EvidenceBadge kind="illustration" detail="planned workflow, not a log" /></div>
              </div>
              <AwaitingResults className="flex-1" title="Execution timeline awaiting Fuzzball logs" artifact="workflow status JSON → snapshot.workflow" note="The Gantt view is reconstructed only from recorded job IDs, timestamps, states and placement." />
            </div>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="fontMono text-[15px] uppercase tracking-[0.2em] text-mute">What Fuzzball contributed</span>
          {contributions.map(({ Icon, label }) => (
            <span key={label} className="flex items-center gap-2 rounded-full border border-[#11A66E]/40 bg-[#11A66E]/10 px-4 py-2 text-[16px] text-ink">
              <Icon size={16} className="text-[#11A66E]" /> {label}
            </span>
          ))}
        </div>
        <div className="fontMono -mt-3 text-[14px] text-mute">Fuzzball orchestrates the workload. Model quality comes from the training itself.</div>
      </div>
    </SlideFrame>
  );
}
