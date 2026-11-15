"use client";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { useSceneClock } from "@/hooks/useSceneClock";
import { dataset, prototype, surrogate } from "@/data/verified/measuredResults";
import type { SlideProps } from "./slideTypes";

const fmt = (n: number) => n.toLocaleString("en-US");

export function SlideScaleUp({ isActive, isPreview, reducedMotion }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 4, maxFps: 30 });
  const scaledTotal = dataset.train + dataset.validation + dataset.test;
  const dataGrowth = (scaledTotal / prototype.scenariosPassed).toFixed(1);
  const protoMin = prototype.arrivalMaeSeconds / 60;
  const scaledMin = surrogate.arrivalMaeSeconds / 60;
  const errorDrop = Math.round((1 - scaledMin / protoMin) * 100);
  const evalGrowth = (surrogate.testSamples / prototype.evalSamples).toFixed(1);

  const columns = [
    {
      tag: "Prototype",
      color: "#C2AFA4",
      rows: [
        ["Simulations", fmt(prototype.scenariosPassed)],
        ["Terrain", `one region (${prototype.region})`],
        ["Scored on", `${prototype.evalSamples} validation scenarios`],
        ["Overlap (IoU)", prototype.iou.toFixed(2)],
      ],
      error: protoMin,
    },
    {
      tag: "Scaled model",
      color: "#48D8FF",
      rows: [
        ["Simulations", fmt(scaledTotal)],
        ["Terrain", "multiple regions"],
        ["Scored on", `${surrogate.testSamples} unseen test simulations`],
        ["Overlap (IoU)", surrogate.iou.toFixed(2)],
      ],
      error: scaledMin,
    },
  ];

  return (
    <SlideFrame
      kicker="Scaling up"
      headline={<>More physics, <span className="cyanText">sharper timing.</span></>}
      lede="Our first prototype learned from one region. Scaling the simulation data cut the arrival-time error by a third, on a broader and larger test."
      aside={<EvidenceBadge kind="verified" detail="measured · different test sets, not a controlled A/B" />}
      reducedMotion={reducedMotion}
      showFooter={false}
    >
      <div className="grid h-full grid-cols-[1fr_auto_1fr_0.9fr] items-stretch gap-6">
        {columns.map((c, k) => (
          <div key={c.tag} className="contents">
            <Reveal show={time > 0.3 + k * 0.9} reducedMotion={reducedMotion}>
              <div className="glassPanel flex h-full flex-col rounded-3xl p-7" style={{ borderColor: `${c.color}55` }}>
                <div className="fontMono text-[16px] uppercase tracking-[0.2em]" style={{ color: c.color }}>{c.tag}</div>
                <div className="mt-4 space-y-3">
                  {c.rows.map(([label, value]) => (
                    <div key={label} className="flex items-baseline justify-between gap-4 border-b border-white/5 pb-2">
                      <span className="text-[19px] text-mute">{label}</span>
                      <span className="fontMono text-[21px] text-ink">{value}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-auto pt-5">
                  <div className="fontMono text-[14px] uppercase tracking-[0.18em] text-mute">Arrival-time error</div>
                  <div className="fontMono text-[64px] font-semibold leading-tight" style={{ color: k === 0 ? "#C2AFA4" : "#48D8FF" }}>{c.error.toFixed(1)} min</div>
                </div>
              </div>
            </Reveal>
            {k === 0 ? (
              <Reveal show={time > 0.8} reducedMotion={reducedMotion} className="flex flex-col items-center justify-center gap-2">
                <ArrowRight size={48} className="text-[#48D8FF]" />
                <span className="fontMono text-[22px] font-semibold text-[#48D8FF]">{dataGrowth}× data</span>
              </Reveal>
            ) : null}
          </div>
        ))}

        <div className="flex flex-col justify-center gap-5">
          {[
            { value: `−${errorDrop}%`, label: "arrival-time error", color: "#35D6A0" },
            { value: `${dataGrowth}×`, label: "more simulations to learn from", color: "#FFB547" },
            { value: `${evalGrowth}×`, label: "larger test, all unseen", color: "#48D8FF" },
          ].map((s, k) => (
            <motion.div
              key={s.label}
              className="glassPanel rounded-2xl px-6 py-4"
              initial={false}
              animate={{ opacity: time > 2 + k * 0.3 ? 1 : 0, x: time > 2 + k * 0.3 ? 0 : 20 }}
              transition={{ duration: reducedMotion ? 0 : 0.6 }}
            >
              <div className="fontMono text-[46px] font-semibold leading-tight" style={{ color: s.color }}>{s.value}</div>
              <div className="text-[19px] text-mute">{s.label}</div>
            </motion.div>
          ))}
          <Reveal show={time > 3} reducedMotion={reducedMotion}>
            <div className="text-[17px] leading-snug text-mute">Burn-area overlap held steady while the test widened from one region to many.</div>
          </Reveal>
        </div>
      </div>
    </SlideFrame>
  );
}
