"use client";
import { motion } from "framer-motion";
import { CircleCheck, CircleDashed, Telescope, ShieldAlert } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { SparkSequence } from "@/components/visualizations/SparkSequence";
import { EmberWordmark } from "@/components/visualizations/EmberLogo";
import { useSceneClock } from "@/hooks/useSceneClock";
import { deriveContributions, futureDirections } from "@/lib/contributions";
import type { SlideProps } from "./slideTypes";

export function Slide14Conclusion({ step, isActive, isPreview, reducedMotion, data }: SlideProps) {
  const contributions = deriveContributions(data);
  const outroTime = useSceneClock({ isActive: isActive && step >= 1, isPreview, reducedMotion, settledTime: 11, resetKey: step });
  const demonstratedCount = contributions.filter((c) => c.demonstrated).length;

  return (
    <>
      <motion.div className="absolute inset-0" initial={false} animate={{ opacity: step >= 1 ? 0 : 1 }} transition={{ duration: reducedMotion ? 0 : 0.6 }}>
        <SlideFrame
          sceneNumber={14}
          kicker="Conclusion · the next frontier"
          headline={<>We didn&apos;t replace physics. <span className="emberText">We made it reusable.</span></>}
          reducedMotion={reducedMotion}
        >
          <div className="grid h-full grid-cols-[1.25fr_1fr] gap-10">
            <div className="glassPanel rounded-2xl p-7">
              <div className="fontMono mb-4 flex justify-between text-[14px] uppercase tracking-[0.2em] text-mute">
                <span>What we demonstrated</span>
                <span>{demonstratedCount}/{contributions.length} evidenced{data.isFixture ? " · FIXTURE" : ""}</span>
              </div>
              <ul className="space-y-3.5">
                {contributions.map((c) => (
                  <li key={c.label} className="flex items-start gap-4">
                    {c.demonstrated ? <CircleCheck size={28} className={data.isFixture ? "text-[#FFB547]" : "text-[#35D6A0]"} /> : <CircleDashed size={28} className="text-dim" />}
                    <div>
                      <div className={`text-[23px] ${c.demonstrated ? "text-ink" : "text-mute"}`}>{c.label}</div>
                      <div className="fontMono text-[14px] text-mute">{c.demonstrated ? `evidence: ${c.evidence}` : `awaiting · ${c.evidence}`}</div>
                    </div>
                  </li>
                ))}
                <li className="flex items-start gap-4">
                  <ShieldAlert size={28} className="text-[#48D8FF]" />
                  <div>
                    <div className="text-[23px] text-ink">Scientific limitations stated</div>
                    <div className="fontMono text-[14px] text-mute">fidelity to simulation ≠ real-world forecast skill</div>
                  </div>
                </li>
              </ul>
            </div>
            <div className="flex flex-col gap-6">
              <div className="glassPanel rounded-2xl p-7">
                <div className="fontMono mb-4 flex items-center gap-2 text-[14px] uppercase tracking-[0.2em] text-[#A78BFA]"><Telescope size={16} /> Proposed future work</div>
                <ul className="space-y-2.5">
                  {futureDirections.map((f) => <li key={f} className="text-[21px] text-ink/90">→ {f}</li>)}
                </ul>
              </div>
              <div className="fontDisplay text-[30px] font-medium leading-snug text-ink">
                Project Ember: from one simulation to a <span className="emberText">scalable scientific-AI workflow.</span>
              </div>
            </div>
          </div>
        </SlideFrame>
      </motion.div>

      {step >= 1 ? (
        <div className="absolute inset-0 bg-void">
          <SparkSequence time={outroTime} showFutures={false} />
          <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at 30% 50%, rgba(8,11,16,0.92) 0%, rgba(8,11,16,0.55) 45%, rgba(8,11,16,0.1) 75%)" }} />
          <div className="absolute left-[120px] top-1/2 -translate-y-1/2">
            <Reveal show={outroTime > 2.8} reducedMotion={reducedMotion}>
              <EmberWordmark scale={1.25} />
            </Reveal>
            <Reveal show={outroTime > 3.8} reducedMotion={reducedMotion} className="mt-10">
              <div className="fontDisplay max-w-[1000px] text-[44px] font-medium leading-tight text-ink">
                From one simulation to a scalable scientific-AI workflow.
              </div>
            </Reveal>
            <Reveal show={outroTime > 4.8} reducedMotion={reducedMotion} className="mt-8">
              <div className="fontMono text-[20px] uppercase tracking-[0.3em] text-mute">Thank you · Questions?</div>
            </Reveal>
          </div>
        </div>
      ) : null}
    </>
  );
}
