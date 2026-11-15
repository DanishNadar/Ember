"use client";
import { motion } from "framer-motion";
import { CircleCheck, Telescope, ShieldAlert } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { SparkSequence } from "@/components/visualizations/SparkSequence";
import { EmberWordmark } from "@/components/visualizations/EmberLogo";
import { useSceneClock } from "@/hooks/useSceneClock";
import { FuzzballLogo, CiqLogo, PartnerStrip } from "@/components/visualizations/BrandMarks";
import { dataset, surrogate, twoNodeRun } from "@/data/verified/measuredResults";
import type { SlideProps } from "./slideTypes";

const demonstrated = [
  { label: `Surrogate trained on ${dataset.train.toLocaleString("en-US")} real ForeFire simulations`, evidence: `held-out IoU ${surrogate.iou.toFixed(2)} · Dice ${surrogate.dice.toFixed(2)} · arrival error ~${Math.round(surrogate.arrivalMaeSeconds / 60)} min` },
  { label: "Physics and AI running at the same time on two nodes", evidence: "CPU ForeFire + GPU training per node, measured overlap" },
  { label: "Fresh labels verified and merged safely", evidence: `+${twoNodeRun.newLabels} train samples · test set untouched` },
  { label: "One model fine-tuned across two GPUs", evidence: `${twoNodeRun.backend} DDP · identical final weights on both ranks` },
];

const team = [
  { name: "Cadence Centers", qr: "/images/team/cadence-qr.png" },
  { name: "Danish Nadar", qr: "/images/team/danish-qr.png" },
  { name: "Sashank Reddy Kadiveti", qr: "/images/team/sashank-qr.png" },
];

const nextSteps = [
  "Run the same workflow under Fuzzball on the two GB10 nodes",
  "Benchmark one vs two nodes on identical work",
  "Larger, terrain-independent evaluation",
  "Real environmental data and physics-informed learning",
];

export function Slide14Conclusion({ step, isActive, isPreview, reducedMotion }: SlideProps) {
  const outroTime = useSceneClock({ isActive: isActive && step >= 1, isPreview, reducedMotion, settledTime: 11, resetKey: step });

  return (
    <>
      <motion.div className="absolute inset-0" initial={false} animate={{ opacity: step >= 1 ? 0 : 1 }} transition={{ duration: reducedMotion ? 0 : 0.6 }}>
        <SlideFrame
          kicker="Conclusion · the next frontier"
          headline={<>We didn&apos;t replace physics. <span className="emberText">We made it reusable.</span></>}
          reducedMotion={reducedMotion}
        >
          <div className="grid h-full grid-cols-[1.25fr_1fr] gap-10">
            <div className="glassPanel rounded-2xl p-7">
              <div className="fontMono mb-4 flex justify-between text-[14px] uppercase tracking-[0.2em] text-mute">
                <span>What we demonstrated</span>
                <span>Measured · Nov 15</span>
              </div>
              <ul className="space-y-3.5">
                {demonstrated.map((c) => (
                  <li key={c.label} className="flex items-start gap-4">
                    <CircleCheck size={28} className="text-[#35D6A0]" />
                    <div>
                      <div className="text-[23px] text-ink">{c.label}</div>
                      <div className="fontMono text-[14px] text-mute">{c.evidence}</div>
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
                <div className="fontMono mb-4 flex items-center gap-2 text-[14px] uppercase tracking-[0.2em] text-[#A78BFA]"><Telescope size={16} /> Next</div>
                <ul className="space-y-2.5">
                  {nextSteps.map((f) => <li key={f} className="text-[21px] text-ink/90">→ {f}</li>)}
                </ul>
              </div>
              <div className="fontDisplay text-[28px] font-medium leading-snug text-ink">
                Project Ember: from one simulation to a <span className="emberText">scalable scientific-AI workflow.</span>
              </div>
              <div className="glassPanel flex items-center gap-6 rounded-2xl px-6 py-4">
                <span className="fontMono text-[13px] uppercase tracking-[0.2em] text-mute">Built with</span>
                <FuzzballLogo height={70} />
                <CiqLogo height={30} />
                <PartnerStrip height={38} className="opacity-85" />
              </div>
            </div>
          </div>
        </SlideFrame>
      </motion.div>

      {step >= 1 ? (
        <div className="absolute inset-0 bg-void">
          <SparkSequence time={outroTime} showFutures={false} />
          <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at 30% 50%, rgba(8,11,16,0.92) 0%, rgba(8,11,16,0.55) 45%, rgba(8,11,16,0.1) 75%)" }} />
          <div className="absolute left-[110px] top-1/2 w-[860px] -translate-y-1/2">
            <Reveal show={outroTime > 2.8} reducedMotion={reducedMotion}>
              <EmberWordmark scale={1.25} />
            </Reveal>
            <Reveal show={outroTime > 3.8} reducedMotion={reducedMotion} className="mt-10">
              <div className="fontDisplay text-[44px] font-medium leading-tight text-ink">
                From one simulation to a scalable scientific-AI workflow.
              </div>
            </Reveal>
            <Reveal show={outroTime > 4.8} reducedMotion={reducedMotion} className="mt-8">
              <div className="fontMono text-[20px] uppercase tracking-[0.3em] text-mute">Thank you · Questions?</div>
            </Reveal>
            <Reveal show={outroTime > 5.6} reducedMotion={reducedMotion} className="mt-14 flex flex-wrap items-center gap-x-8 gap-y-5">
              <span className="fontMono text-[14px] uppercase tracking-[0.2em] text-mute">Orchestrated with</span>
              <FuzzballLogo height={88} />
              <CiqLogo height={34} />
              <PartnerStrip height={44} className="opacity-85" />
            </Reveal>
          </div>
          <Reveal show={outroTime > 4.4} reducedMotion={reducedMotion} className="absolute right-[90px] top-1/2 -translate-y-1/2">
            <div className="fontMono mb-5 text-center text-[16px] uppercase tracking-[0.28em] text-mute">Connect with the team</div>
            <div className="flex gap-5">
              {team.map((m) => (
                <div key={m.name} className="glassPanel flex w-[226px] flex-col items-center rounded-2xl p-4">
                  <div className="rounded-xl bg-white p-3">
                    <img src={m.qr} alt={`LinkedIn QR code for ${m.name}`} width={172} height={172} style={{ width: 172, height: 172, imageRendering: "pixelated" }} />
                  </div>
                  <div className="fontDisplay mt-3 text-center text-[20px] font-semibold leading-tight text-ink">{m.name}</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      ) : null}
    </>
  );
}
