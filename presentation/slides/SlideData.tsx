"use client";
import { motion } from "framer-motion";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { useSceneClock } from "@/hooks/useSceneClock";
import { dataset } from "@/data/verified/measuredResults";
import type { SlideProps } from "./slideTypes";

const fmt = (n: number) => n.toLocaleString("en-US");

export function SlideData({ isActive, isPreview, reducedMotion }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 4, maxFps: 30 });
  const total = dataset.train + dataset.validation + dataset.test;
  const splits = [
    { label: "Train", value: dataset.train, color: "#FF6B35" },
    { label: "Validation", value: dataset.validation, color: "#FFB547" },
    { label: "Held-out test", value: dataset.test, color: "#48D8FF" },
  ];
  const facts = [
    { value: String(dataset.channels), label: "input channels", hint: "fuel, moisture, terrain slope, wind + a mid-run wind shift, ignition" },
    { value: `${dataset.grid}×${dataset.grid}`, label: "grid", hint: `${dataset.cellMeters} m cells · ${(dataset.grid * dataset.cellMeters) / 1000} km square` },
    { value: `${dataset.horizonMinutes} min`, label: "forecast horizon", hint: "per simulation" },
    { value: "2", label: "targets", hint: "burned area + arrival time" },
  ];
  const showBar = time > 1.2;

  return (
    <SlideFrame
      kicker="The data"
      headline={<>Real physics. <span className="emberText">Real labels.</span></>}
      lede={`Every training example is a genuine ${dataset.simulator} run on real terrain: ${dataset.regions.join(", ")}.`}
      aside={<EvidenceBadge kind="verified" detail="file counts checked · Nov 15" />}
      reducedMotion={reducedMotion}
    >
      <div className="grid h-full grid-cols-[1.15fr_1fr] gap-10">
        <div className="flex flex-col justify-center gap-8">
          <Reveal show={time > 0.2} reducedMotion={reducedMotion}>
            <div className="fontMono text-[16px] uppercase tracking-[0.2em] text-mute">Candidate conditions prepared</div>
            <div className="fontMono text-[64px] font-semibold leading-tight text-ink/60">~{fmt(dataset.candidateScenarios)}</div>
          </Reveal>
          <Reveal show={time > 0.7} reducedMotion={reducedMotion}>
            <div className="fontMono text-[16px] uppercase tracking-[0.2em] text-mute">Completed, retained simulations</div>
            <div className="fontMono text-[88px] font-semibold leading-tight text-[#FFB547]">{fmt(total)}</div>
          </Reveal>
          <div>
            <div className="flex h-14 overflow-hidden rounded-xl bg-white/5">
              {splits.map((s, k) => (
                <motion.div
                  key={s.label}
                  className="h-full"
                  style={{ background: s.color, opacity: 0.85 }}
                  initial={false}
                  animate={{ width: showBar ? `${(s.value / total) * 100}%` : "0%" }}
                  transition={{ duration: reducedMotion ? 0 : 0.8, delay: reducedMotion ? 0 : k * 0.25 }}
                />
              ))}
            </div>
            <Reveal show={showBar} reducedMotion={reducedMotion} className="mt-4 flex gap-8">
              {splits.map((s) => (
                <div key={s.label} className="flex items-center gap-3 text-[22px] text-ink">
                  <span className="inline-block h-4 w-4 rounded" style={{ background: s.color }} />
                  {s.label} <span className="fontMono text-mute">{fmt(s.value)}</span>
                </div>
              ))}
            </Reveal>
            <Reveal show={showBar} reducedMotion={reducedMotion} className="mt-3 text-[19px] text-mute">
              The test set is never used for training or model selection.
            </Reveal>
          </div>
        </div>
        <div className="grid grid-cols-2 content-center gap-5">
          {facts.map((f, k) => (
            <Reveal key={f.label} show={time > 1.6 + k * 0.3} reducedMotion={reducedMotion}>
              <div className="glassPanel rounded-2xl p-6">
                <div className="fontMono text-[48px] font-semibold leading-none text-ink">{f.value}</div>
                <div className="fontMono mt-3 text-[16px] uppercase tracking-[0.18em] text-[#FFB547]">{f.label}</div>
                <div className="mt-2 text-[19px] text-mute">{f.hint}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </SlideFrame>
  );
}
