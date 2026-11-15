"use client";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { useSceneClock } from "@/hooks/useSceneClock";
import { dataset, fineTuned, prototype, surrogate } from "@/data/verified/measuredResults";
import type { SlideProps } from "./slideTypes";

const fmt = (n: number) => n.toLocaleString("en-US");

export function SlideScaleUp({ isActive, isPreview, reducedMotion }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 4.5, maxFps: 30 });
  const scaledTotal = dataset.train + dataset.validation + dataset.test;
  const dataGrowth = (scaledTotal / prototype.scenariosPassed).toFixed(1);
  const protoMin = prototype.arrivalMaeSeconds / 60;
  const finalMin = fineTuned.arrivalMaeSeconds / 60;
  const errorDrop = Math.round((1 - finalMin / protoMin) * 100);

  const stages = [
    {
      tag: "① Prototype",
      color: "#C2AFA4",
      trained: `${fmt(prototype.scenariosPassed)} simulations, one region`,
      scored: `${prototype.evalSamples} validation scenarios`,
      iou: prototype.iou,
      dice: null as number | null,
      precision: null as number | null,
      minutes: protoMin,
    },
    {
      tag: "② Scaled",
      color: "#FFB547",
      trained: `${fmt(scaledTotal)} simulations, multiple regions`,
      scored: `${surrogate.testSamples} unseen test simulations`,
      iou: surrogate.iou,
      dice: surrogate.dice as number | null,
      precision: surrogate.precision as number | null,
      minutes: surrogate.arrivalMaeSeconds / 60,
    },
    {
      tag: "③ Fine-tuned on two GPUs",
      color: "#48D8FF",
      trained: `+ ${fineTuned.trainSamples} samples incl. fresh labels`,
      scored: `${fineTuned.testSamples} unseen test simulations`,
      iou: fineTuned.iou,
      dice: fineTuned.dice as number | null,
      precision: fineTuned.precision as number | null,
      minutes: finalMin,
    },
  ];

  const highlights = [
    { value: `−${errorDrop}%`, label: "arrival-time error, prototype → latest", color: "#35D6A0" },
    { value: `${prototype.iou.toFixed(2)} → ${fineTuned.iou.toFixed(2)}`, label: "burn-area overlap (IoU)", color: "#48D8FF" },
    { value: `${Math.round(surrogate.precision * 100)}%`, label: `precision on ${surrogate.testSamples} unseen simulations`, color: "#FFB547" },
    { value: `${dataGrowth}×`, label: "more simulations to learn from", color: "#FFB547" },
  ];

  return (
    <SlideFrame
      kicker="Scaling up"
      headline={<>More physics, <span className="cyanText">a sharper model.</span></>}
      lede="Three generations: a one-region prototype, a model scaled on far more simulations, then fine-tuned across two GPUs on fresh labels."
      aside={<EvidenceBadge kind="verified" detail="measured · each stage scored on its own unseen set" />}
      reducedMotion={reducedMotion}
      showFooter={false}
    >
      <div className="flex h-full flex-col gap-6">
        <div className="grid min-h-0 flex-1 grid-cols-[1fr_auto_1fr_auto_1fr] gap-4">
          {stages.map((s, k) => (
            <div key={s.tag} className="contents">
              <Reveal show={time > 0.3 + k * 0.8} reducedMotion={reducedMotion}>
                <div
                  className="glassPanel flex h-full flex-col rounded-3xl p-6"
                  style={{ borderColor: `${s.color}55`, boxShadow: k === 2 ? `0 0 70px -24px ${s.color}` : undefined }}
                >
                  <div className="fontMono text-[16px] uppercase tracking-[0.18em]" style={{ color: s.color }}>{s.tag}</div>
                  <div className="mt-3 text-[19px] leading-snug text-ink">{s.trained}</div>
                  <div className="text-[17px] text-mute">scored on {s.scored}</div>
                  <div className="mt-auto pt-4">
                    <div className="fontMono text-[13px] uppercase tracking-[0.18em] text-mute">Arrival error</div>
                    <div className="fontMono text-[50px] font-semibold leading-none" style={{ color: s.color }}>{s.minutes.toFixed(1)}<span className="text-[24px]"> min</span></div>
                    <div className="mt-4 grid grid-cols-3 gap-2">
                      {([["Precision", s.precision], ["Dice", s.dice], ["IoU", s.iou]] as const).map(([label, v]) => (
                        <div key={label}>
                          <div className="fontMono text-[12px] uppercase tracking-[0.16em] text-mute">{label}</div>
                          <div className={`fontMono text-[28px] font-semibold leading-tight ${v === null ? "text-dim" : "text-ink"}`}>{v === null ? "—" : v.toFixed(2)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </Reveal>
              {k < stages.length - 1 ? (
                <Reveal show={time > 0.7 + k * 0.8} reducedMotion={reducedMotion} className="flex items-center">
                  <ChevronRight size={40} className="text-mute" />
                </Reveal>
              ) : null}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-4 gap-5">
          {highlights.map((h, k) => (
            <motion.div
              key={h.label}
              className="glassPanel rounded-2xl px-6 py-4"
              initial={false}
              animate={{ opacity: time > 2.8 + k * 0.25 ? 1 : 0, y: time > 2.8 + k * 0.25 ? 0 : 14 }}
              transition={{ duration: reducedMotion ? 0 : 0.6 }}
            >
              <div className="fontMono text-[40px] font-semibold leading-tight" style={{ color: h.color }}>{h.value}</div>
              <div className="text-[18px] text-mute">{h.label}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </SlideFrame>
  );
}
