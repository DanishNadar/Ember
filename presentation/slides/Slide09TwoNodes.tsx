"use client";
import { useEffect, useMemo, useState } from "react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { AwaitingResults } from "@/components/presentation/AwaitingResults";
import { SegmentedToggle } from "@/components/controls/SegmentedToggle";
import { ComputeNode } from "@/components/visualizations/ComputeNode";
import { useSceneClock } from "@/hooks/useSceneClock";
import type { WorkflowJob } from "@/data/schemas/presentationSchema";
import { FuzzballMark } from "@/components/visualizations/BrandMarks";
import { fuzzballGreen } from "@/lib/ecosystem";
import type { SlideProps } from "./slideTypes";

const plannedStages = ["Simulate scenarios", "Publish shards", "Stage dataset", "Train surrogate", "Evaluate", "Complete"];
const stageColor: Record<WorkflowJob["stage"], string> = {
  simulation: "#FF6B35", dataset: "#FFB547", training: "#48D8FF", evaluation: "#35D6A0", inference: "#48D8FF", other: "#94A3B8",
};

function PlannedView({ time }: { time: number }) {
  const cycle = 7.5;
  const t = time % cycle;
  const stageIndex = Math.min(plannedStages.length - 1, Math.floor((t / cycle) * plannedStages.length));
  const packets = Array.from({ length: 7 }, (_, k) => ((time * 0.32 + k / 7) % 1));
  const leftX = 60;
  const rightX = 1198;
  const nodeW = 470;
  const laneY = 330;

  return (
    <div className="relative h-full">
      {/* Fuzzball control plane */}
      <div className="glassPanel absolute left-1/2 top-0 flex -translate-x-1/2 items-center gap-4 rounded-2xl px-7 py-4">
        <FuzzballMark size={46} />
        <div>
          <div className="fontDisplay text-[26px] font-semibold text-ink">Fuzzball Orchestrate</div>
          <div className="fontMono text-[14px] text-mute">schedules jobs · provisions resources · stages volumes</div>
        </div>
      </div>
      <svg className="absolute inset-0" width={1728} height={680}>
        <path d={`M864,86 C864,150 ${leftX + nodeW / 2},140 ${leftX + nodeW / 2},178`} stroke={fuzzballGreen} strokeOpacity={0.7} strokeWidth={2} fill="none" className="flowDash" />
        <path d={`M864,86 C864,150 ${rightX + nodeW / 2},140 ${rightX + nodeW / 2},178`} stroke={fuzzballGreen} strokeOpacity={0.7} strokeWidth={2} fill="none" className="flowDash" />
        <line x1={leftX + nodeW + 10} y1={laneY} x2={rightX - 10} y2={laneY} stroke="#FFB547" strokeOpacity={0.2} strokeWidth={22} strokeLinecap="round" />
        {packets.map((p, k) => (
          <g key={k} transform={`translate(${leftX + nodeW + 20 + p * (rightX - leftX - nodeW - 40)}, ${laneY})`} opacity={Math.sin(p * Math.PI)}>
            <rect x={-16} y={-11} width={32} height={22} rx={4} fill="#FFB547" />
            <rect x={-10} y={-5} width={20} height={3} fill="#080B10" opacity={0.6} />
            <rect x={-10} y={1} width={14} height={3} fill="#080B10" opacity={0.6} />
          </g>
        ))}
        <text x={864} y={laneY - 30} textAnchor="middle" className="fontMono" fontSize={17} fill="#FFB547">simulation shards → Fuzzball volume → dataset</text>
        <text x={864} y={laneY + 46} textAnchor="middle" className="fontMono" fontSize={15} fill="#94A3B8">produced, published, consumed while simulation continues</text>
      </svg>
      <div className="absolute" style={{ left: leftX, top: 180 }}>
        <ComputeNode label="Node A" role="Simulation" color="#FF6B35" activity={stageIndex <= 2 ? 0.9 : 0.55} />
      </div>
      <div className="absolute" style={{ left: rightX, top: 180 }}>
        <ComputeNode label="Node B" role="Neural optimization" color="#48D8FF" activity={stageIndex >= 3 ? 0.95 : 0.3} />
      </div>
      <div className="absolute bottom-0 left-0 right-0 flex justify-center gap-3">
        {plannedStages.map((stage, k) => (
          <div key={stage} className={`fontMono rounded-full border px-4 py-2 text-[15px] transition ${k === stageIndex ? "border-ember bg-ember/15 text-ink" : k < stageIndex ? "border-white/15 text-mute" : "border-white/5 text-dim"}`}>
            {k + 1}. {stage}
          </div>
        ))}
      </div>
    </div>
  );
}

function VerifiedView({ data }: { data: SlideProps["data"] }) {
  const workflow = data.snapshot.workflow;
  const byNode = useMemo(() => {
    const groups = new Map<string, WorkflowJob[]>();
    workflow?.jobs.forEach((job) => {
      const key = job.node ?? "placement not recorded";
      groups.set(key, [...(groups.get(key) ?? []), job]);
    });
    return Array.from(groups.entries());
  }, [workflow]);

  if (!workflow) {
    return (
      <AwaitingResults
        className="h-full"
        title="Verified execution awaiting Fuzzball logs"
        artifact="Fuzzball workflow status / logs → snapshot.workflow"
        note="This view is generated only from recorded logs. Until then we make no claim about node placement, concurrency or GPU saturation."
      />
    );
  }

  const recordedNodes = byNode.filter(([node]) => node !== "placement not recorded").length;
  return (
    <div className="flex h-full flex-col gap-5">
      <div className="flex items-center gap-4 text-[20px] text-mute">
        <span className="fontMono text-ink">{workflow.workflowId}</span>
        <span>· {workflow.jobs.length} jobs · {recordedNodes} node{recordedNodes === 1 ? "" : "s"} recorded · mode: <span className="text-ink">{workflow.executionMode}</span></span>
        <span className="ml-auto"><EvidenceBadge kind={data.evidenceFor("workflow")} isFixture={data.isFixture} detail={`recorded playback · ${workflow.source.path}`} /></span>
      </div>
      {recordedNodes === 1 ? (
        <div className="fontMono rounded-xl border border-[#FFB547]/40 bg-[#FFB547]/10 px-5 py-3 text-[17px] text-[#FFB547]">
          Logs show all jobs on a single node. The two-node design is shown as planned only.
        </div>
      ) : null}
      <div className="grid min-h-0 flex-1 gap-5" style={{ gridTemplateColumns: `repeat(${Math.max(1, byNode.length)}, minmax(0, 1fr))` }}>
        {byNode.map(([node, jobs]) => (
          <div key={node} className="glassPanel min-h-0 overflow-y-auto rounded-2xl p-5">
            <div className="fontDisplay mb-3 text-[26px] font-semibold text-ink">{node}</div>
            <ul className="space-y-2">
              {jobs.map((job) => (
                <li key={job.id} className="flex items-center gap-3 rounded-lg bg-white/[0.03] px-3 py-2">
                  <span className="inline-block h-3 w-3 rounded-sm" style={{ background: stageColor[job.stage] }} />
                  <span className="text-[18px] text-ink">{job.name}</span>
                  <span className="fontMono ml-auto text-[14px] text-mute">{job.state}{job.resources?.gpu ? ` · ${job.resources.gpu} GPU` : ""}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Slide09TwoNodes({ isActive, isPreview, reducedMotion, data }: SlideProps) {
  const [view, setView] = useState<"planned" | "verified">("planned");
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 3.2, maxFps: 30 });
  useEffect(() => {
    if (!isActive) setView("planned");
  }, [isActive]);

  return (
    <SlideFrame
      sceneNumber={9}
      kicker="The two-node experiment"
      headline={<>Two nodes. <span className="emberText">One continuous experiment.</span></>}
      aside={
        <div className="flex flex-col items-end gap-3">
          <SegmentedToggle options={[["planned", "Planned architecture"], ["verified", "Verified execution"]]} value={view} onChange={setView} />
          {view === "planned" ? <EvidenceBadge kind="illustration" detail="conceptual design" /> : null}
        </div>
      }
      reducedMotion={reducedMotion}
    >
      {view === "planned" ? <PlannedView time={time} /> : <VerifiedView data={data} />}
    </SlideFrame>
  );
}
