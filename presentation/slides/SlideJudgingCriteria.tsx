"use client";
import { CircleCheck, CircleDashed, MessageSquareQuote } from "lucide-react";
import { motion } from "framer-motion";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { FuzzballMark, PartnerStrip } from "@/components/visualizations/BrandMarks";
import { judgingCriteria, layerStatus, stackLayers, usageStatusStyle, fuzzballGreen } from "@/lib/ecosystem";
import type { PresentationData } from "@/data/adapters/presentationData";
import type { SlideProps } from "./slideTypes";

type Point = { text: string; kind: "evidenced" | "awaiting" | "narrative"; note?: string };

function pointsFor(id: (typeof judgingCriteria)[number]["id"], data: PresentationData): Point[] {
  const s = data.snapshot;
  const ev = (ok: boolean): Point["kind"] => (ok && !data.isFixture ? "evidenced" : "awaiting");
  const nodes = new Set((s.workflow?.jobs ?? []).map((j) => j.node).filter(Boolean)).size;
  switch (id) {
    case "technical":
      return [
        { text: "End-to-end pipeline: simulate → dataset → U-Net → evaluate", kind: ev(Boolean(s.dataset && s.model)), note: "manifest + model metadata" },
        { text: "Held-out fidelity: IoU, precision, recall, F2", kind: ev(Boolean(s.fidelity)), note: "metrics/results.json" },
        { text: "Recorded multi-stage Fuzzball workflow", kind: ev(Boolean(s.workflow)), note: s.workflow ? `${s.workflow.jobs.length} jobs` : "workflow logs" },
        { text: "Measured runtimes, with training cost shown separately", kind: ev(Boolean(s.benchmarks)), note: "benchmarks" },
      ];
    case "ecosystem":
      return [];
    case "impact":
      return [
        { text: "Faster what-if exploration of wildfire spread under uncertain conditions", kind: "narrative" },
        { text: "Ensemble agreement maps show where outcomes are robust", kind: s.ensemble ? ev(true) : "narrative", note: s.ensemble ? "ensemble outputs" : "proposed extension" },
        { text: "Honest limits: fidelity to simulation ≠ forecast skill", kind: "narrative" },
      ];
    case "innovation":
      return [
        { text: "Physics-trained neural surrogate replaces repeated simulation calls", kind: ev(Boolean(s.fidelity)) },
        { text: "Producer–consumer overlap via Fuzzball depends-on: RUNNING", kind: ev(Boolean(data.workflowSpeedup && data.workflowSpeedup.ratio > 1)), note: "sequential vs overlapping run" },
        { text: "Two-node placement: simulation on A, learning on B", kind: ev(nodes >= 2), note: nodes >= 2 ? `${nodes} nodes in logs` : "node placement in logs" },
      ];
  }
}

const kindIcon = {
  evidenced: <CircleCheck size={20} className="shrink-0 text-[#35D6A0]" />,
  awaiting: <CircleDashed size={20} className="shrink-0 text-dim" />,
  narrative: <MessageSquareQuote size={20} className="shrink-0 text-[#94A3B8]" />,
};

export function SlideJudgingCriteria({ reducedMotion, data }: SlideProps) {
  return (
    <SlideFrame
      kicker="Official evaluation criteria · SC26 Local AI Hackathon"
      headline={<>Built for <span className="emberText">every criterion.</span></>}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full flex-col gap-5">
        <div className="grid flex-1 grid-cols-4 gap-5">
          {judgingCriteria.map((criterion, k) => (
            <motion.div
              key={criterion.id}
              initial={reducedMotion ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: reducedMotion ? 0 : 0.15 + k * 0.1 }}
              className="glassPanel flex flex-col rounded-2xl p-6"
              style={criterion.id === "ecosystem" ? { borderTop: `3px solid ${fuzzballGreen}` } : { borderTop: "3px solid #FF6B35" }}
            >
              <div className="fontMono text-[14px] text-mute">0{k + 1}</div>
              <div className="fontDisplay mt-1 text-[25px] font-semibold leading-tight text-ink">{criterion.title}</div>
              <div className="mt-1 text-[15px] italic leading-snug text-mute">{criterion.question}</div>
              <div className="my-4 h-px bg-white/10" />
              {criterion.id === "ecosystem" ? (
                <ul className="space-y-2">
                  {stackLayers.filter((l) => l.id !== "ember").map((l) => {
                    const st = layerStatus(l.id, data.snapshot);
                    const style = usageStatusStyle[st.status];
                    return (
                      <li key={l.id} className="flex items-start gap-2.5">
                        {l.logo === "fuzzball" ? <FuzzballMark size={18} className="mt-0.5 shrink-0" /> : <span className="mt-1.5 inline-block h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: l.color }} />}
                        <div className="min-w-0">
                          <div className="text-[15.5px] leading-tight text-ink/95">{l.title}</div>
                          <div className="fontMono text-[11.5px]" style={{ color: style.color }}>{style.label}</div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <ul className="space-y-3.5">
                  {pointsFor(criterion.id, data).map((p) => (
                    <li key={p.text} className="flex items-start gap-2.5">
                      {kindIcon[p.kind]}
                      <div>
                        <div className={`text-[17px] leading-snug ${p.kind === "awaiting" ? "text-mute" : "text-ink/95"}`}>{p.text}</div>
                        {p.note ? <div className="fontMono text-[12px] text-dim">{p.kind === "awaiting" ? `awaiting · ${p.note}` : p.note}</div> : null}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </motion.div>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <div className="fontMono flex gap-6 text-[13px] text-mute">
            <span className="flex items-center gap-1.5"><CircleCheck size={14} className="text-[#35D6A0]" /> evidenced by ingested artifacts</span>
            <span className="flex items-center gap-1.5"><CircleDashed size={14} /> awaiting artifact</span>
            <span className="flex items-center gap-1.5"><MessageSquareQuote size={14} /> argument / design</span>
          </div>
          <PartnerStrip height={40} className="opacity-80" />
        </div>
      </div>
    </SlideFrame>
  );
}
