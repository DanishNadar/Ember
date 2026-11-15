"use client";
import { motion } from "framer-motion";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { MetricStat } from "@/components/charts/MetricStat";
import { useSceneClock } from "@/hooks/useSceneClock";
import { surrogate } from "@/data/verified/measuredResults";
import type { SlideProps } from "./slideTypes";

const bars = [
  { label: "Precision", value: surrogate.precision, color: "#35D6A0", read: "When it predicts fire, it's usually right." },
  { label: "Dice", value: surrogate.dice, color: "#48D8FF", read: "Overall overlap of predicted vs simulated burn area." },
  { label: "Recall", value: surrogate.recall, color: "#FFB547", read: "It's conservative: it misses some burned area." },
  { label: "IoU", value: surrogate.iou, color: "#FF6B35", read: "The strictest overlap score." },
];

export function SlideSurrogateResults({ isActive, isPreview, reducedMotion }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 4, maxFps: 30 });
  const show = time > 0.4;

  return (
    <SlideFrame
      kicker="The results"
      headline={<>How close did <span className="cyanText">AI</span> get?</>}
      lede={`Scored against ${surrogate.testSamples} held-out ForeFire simulations the model never saw.`}
      aside={<EvidenceBadge kind="verified" detail={`${surrogate.testSamples} held-out simulations`} />}
      reducedMotion={reducedMotion}
      showFooter={false}
    >
      <div className="grid h-full grid-cols-[1.35fr_1fr] gap-10">
        <div className="flex flex-col justify-center gap-6">
          {bars.map((b, k) => (
            <div key={b.label}>
              <div className="mb-2 flex items-baseline justify-between">
                <span className="fontDisplay text-[30px] font-semibold text-ink">{b.label}</span>
                <span className="fontMono text-[34px] font-semibold tabular-nums" style={{ color: b.color }}>{b.value.toFixed(2)}</span>
              </div>
              <div className="h-5 overflow-hidden rounded-full bg-white/5">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: b.color, boxShadow: `0 0 18px ${b.color}88` }}
                  initial={false}
                  animate={{ width: show ? `${b.value * 100}%` : "0%" }}
                  transition={{ duration: reducedMotion ? 0 : 0.9, delay: reducedMotion ? 0 : k * 0.15 }}
                />
              </div>
              <div className="mt-1.5 text-[19px] text-mute">{b.read}</div>
            </div>
          ))}
        </div>
        <div className="flex flex-col justify-center gap-6">
          <Reveal show={time > 1} reducedMotion={reducedMotion}>
            <div className="glassPanel rounded-2xl p-7">
              <MetricStat label="Arrival-time error" value={surrogate.arrivalMaeSeconds / 60} format={(v) => `~${v.toFixed(1)} min`} active={show} reducedMotion={reducedMotion} size="lg" color="#48D8FF" hint="mean absolute error on cells the fire reached, over a 60-minute horizon" />
            </div>
          </Reveal>
          <Reveal show={time > 1.5} reducedMotion={reducedMotion}>
            <div className="glassPanel grid grid-cols-2 gap-5 rounded-2xl p-7">
              <MetricStat label="Training" value={surrogate.trainMinutes} format={(v) => `${v.toFixed(1)} min`} active={show} reducedMotion={reducedMotion} size="sm" hint={`${surrogate.epochs} epochs · one GPU`} />
              <MetricStat label="Model size" value={surrogate.checkpointMB} format={(v) => `${v.toFixed(1)} MB`} active={show} reducedMotion={reducedMotion} size="sm" hint="two-head U-Net" />
            </div>
          </Reveal>
          <Reveal show={time > 2} reducedMotion={reducedMotion}>
            <div className="fontMono rounded-xl border border-white/10 px-5 py-3 text-[16px] leading-relaxed text-mute">
              Agreement with the ForeFire simulator, not real-world forecast skill.
            </div>
          </Reveal>
        </div>
      </div>
    </SlideFrame>
  );
}
