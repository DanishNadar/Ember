"use client";
import { motion } from "framer-motion";
import { Cpu, BrainCircuit, ShieldCheck, ArrowLeftRight } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { twoNodeRun } from "@/data/verified/measuredResults";
import type { SlideProps } from "./slideTypes";

function Phase({ show, reducedMotion, children, className = "" }: { show: boolean; reducedMotion: boolean; children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={false}
      animate={{ opacity: show ? 1 : 0.12, filter: show ? "blur(0px)" : "blur(2px)" }}
      transition={{ duration: reducedMotion ? 0 : 0.6 }}
    >
      {children}
    </motion.div>
  );
}

export function SlideTwoNodeRun({ step, reducedMotion }: SlideProps) {
  const r = twoNodeRun;
  const stats = [
    { value: "2", label: "GPU nodes", color: "#F3F6FA" },
    { value: `+${r.newLabels}`, label: "fresh simulator labels", color: "#FFB547" },
    { value: `${r.worldSize} ranks`, label: `${r.backend} · identical final weights`, color: "#48D8FF" },
    { value: r.elapsed, label: "end to end", color: "#35D6A0" },
  ];

  return (
    <SlideFrame
      kicker="Scaling out"
      headline={<>Two nodes. <span className="emberText">One model.</span></>}
      lede="Simulate and train at the same time on both nodes, verify the new labels, then fine-tune one model across both GPUs."
      aside={<EvidenceBadge kind="verified" detail="two-node test run · Nov 15" />}
      reducedMotion={reducedMotion}
      showFooter={false}
    >
      <div className="flex h-full flex-col gap-6">
        <div className="grid min-h-0 flex-1 grid-cols-[1.45fr_0.8fr_1.1fr] gap-5">
          {/* Phase 1: per-node CPU physics + GPU training, concurrently */}
          <Phase show={step >= 0} reducedMotion={reducedMotion} className="flex flex-col gap-4">
            <div className="fontMono text-[15px] uppercase tracking-[0.2em] text-[#FF6B35]">① Both nodes: physics + AI at once</div>
            {r.nodes.map((n) => {
              const share = n.overlapSeconds / n.phaseSeconds;
              return (
                <div key={n.name} className="glassPanel flex-1 rounded-2xl p-5">
                  <div className="fontMono mb-3 text-[16px] text-mute">{n.name} · rank {n.rank}</div>
                  <div className="flex items-center gap-3 text-[21px] text-ink"><Cpu size={22} className="text-[#FF6B35]" /> ForeFire simulations <span className="fontMono text-[15px] text-mute">CPU</span></div>
                  <div className="mt-1.5 flex items-center gap-3 text-[21px] text-ink"><BrainCircuit size={22} className="text-[#48D8FF]" /> Surrogate training <span className="fontMono text-[15px] text-mute">GPU</span></div>
                  <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-white/5">
                    <motion.div className="h-full rounded-full" style={{ background: "linear-gradient(90deg,#FF6B35,#48D8FF)" }} initial={false} animate={{ width: `${share * 100}%` }} transition={{ duration: reducedMotion ? 0 : 0.9 }} />
                  </div>
                  <div className="fontMono mt-1.5 text-[15px] text-mute">running together {n.overlapSeconds.toFixed(2)} s of {n.phaseSeconds.toFixed(1)} s</div>
                </div>
              );
            })}
          </Phase>

          {/* Barrier: verify + merge */}
          <Phase show={step >= 1} reducedMotion={reducedMotion} className="flex flex-col gap-4">
            <div className="fontMono text-[15px] uppercase tracking-[0.2em] text-[#FFB547]">② Verify + merge</div>
            <div className="glassPanel flex flex-1 flex-col justify-center rounded-2xl p-6" style={{ borderColor: "#FFB54766" }}>
              <ShieldCheck size={40} className="mb-3 text-[#FFB547]" />
              <div className="fontMono text-[22px] text-ink">{r.stagedTrain} + <span className="text-[#FFB547]">{r.newLabels}</span> = {r.mergedTrain}</div>
              <div className="mt-1 text-[19px] text-mute">training samples</div>
              <div className="mt-4 text-[19px] leading-snug text-mute">Shapes, values and duplicates checked. Validation and test sets untouched.</div>
            </div>
          </Phase>

          {/* Phase 2: one model, two GPU ranks */}
          <Phase show={step >= 2} reducedMotion={reducedMotion} className="flex flex-col gap-4">
            <div className="fontMono text-[15px] uppercase tracking-[0.2em] text-[#48D8FF]">③ Distributed fine-tuning</div>
            <div className="glassPanel flex flex-1 flex-col justify-center rounded-2xl p-6" style={{ borderColor: "#48D8FF66", boxShadow: "0 0 60px -20px #48D8FF" }}>
              <div className="flex items-center justify-between gap-3">
                {r.nodes.map((n, k) => (
                  <div key={n.name} className="contents">
                    <div className="rounded-xl border border-[#48D8FF]/40 bg-[#48D8FF]/10 px-4 py-3 text-center">
                      <div className="fontMono text-[15px] text-mute">rank {n.rank}</div>
                      <div className="fontDisplay text-[24px] font-semibold text-ink">{n.name}</div>
                    </div>
                    {k === 0 ? <ArrowLeftRight size={34} className="text-[#48D8FF]" /> : null}
                  </div>
                ))}
              </div>
              <div className="mt-5 text-[22px] text-ink">One model, PyTorch DDP over {r.backend}.</div>
              <div className="fontMono mt-2 text-[15px] leading-relaxed text-mute">final weights SHA-256 identical on both ranks<br />{r.weightSha}</div>
            </div>
          </Phase>
        </div>

        <Phase show={step >= 2} reducedMotion={reducedMotion} className="grid grid-cols-4 gap-5">
          {stats.map((s) => (
            <div key={s.label} className="glassPanel rounded-2xl px-6 py-4">
              <div className="fontMono text-[36px] font-semibold leading-tight" style={{ color: s.color }}>{s.value}</div>
              <div className="text-[18px] text-mute">{s.label}</div>
            </div>
          ))}
        </Phase>
      </div>
    </SlideFrame>
  );
}
