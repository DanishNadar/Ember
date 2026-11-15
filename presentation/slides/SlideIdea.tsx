"use client";
import { ArrowRight, Cpu, Database, BrainCircuit, RefreshCw } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { useSceneClock } from "@/hooks/useSceneClock";
import type { SlideProps } from "./slideTypes";

const stages = [
  { Icon: Cpu, color: "#FF6B35", tag: "CPU · physics", title: "ForeFire simulator", body: "Exact fire physics. One future per run, and every run costs compute." },
  { Icon: Database, color: "#FFB547", tag: "Data", title: "Labeled examples", body: "Conditions in → where and when the fire arrives out." },
  { Icon: BrainCircuit, color: "#48D8FF", tag: "GPU · AI", title: "Neural surrogate", body: "A U-Net learns the pattern and answers in a single forward pass." },
];

export function SlideIdea({ isActive, isPreview, reducedMotion }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 4, maxFps: 20 });

  return (
    <SlideFrame
      kicker="The idea"
      headline={<>Let physics teach. <span className="cyanText">Let AI learn.</span></>}
      lede="Ember turns an expensive physics simulator into training data for a fast neural surrogate, and runs both at once on two nodes."
      aside={<EvidenceBadge kind="illustration" detail="concept" />}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full flex-col justify-center gap-10">
        <div className="flex items-stretch gap-5">
          {stages.map(({ Icon, color, tag, title, body }, k) => (
            <div key={title} className="contents">
              <Reveal show={time > 0.3 + k * 0.6} reducedMotion={reducedMotion} className="flex-1">
                <div className="glassPanel h-full rounded-3xl p-8" style={{ borderColor: `${color}55` }}>
                  <div className="mb-5 flex items-center gap-4">
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl" style={{ background: `${color}1f`, boxShadow: `0 0 30px -6px ${color}` }}>
                      <Icon size={34} color={color} />
                    </div>
                    <div className="fontMono text-[15px] uppercase tracking-[0.2em]" style={{ color }}>{tag}</div>
                  </div>
                  <div className="fontDisplay text-[38px] font-semibold text-ink">{title}</div>
                  <div className="mt-3 text-[24px] leading-snug text-mute">{body}</div>
                </div>
              </Reveal>
              {k < stages.length - 1 ? (
                <Reveal show={time > 0.6 + k * 0.6} reducedMotion={reducedMotion} className="flex items-center">
                  <ArrowRight size={44} className="text-mute" />
                </Reveal>
              ) : null}
            </div>
          ))}
        </div>
        <Reveal show={time > 2.3} reducedMotion={reducedMotion}>
          <div className="glassPanel flex items-center gap-5 rounded-2xl px-8 py-5">
            <RefreshCw size={30} className="text-[#35D6A0]" />
            <div className="text-[26px] text-ink">
              The loop: <span className="text-[#FF6B35]">new simulations</span> keep producing <span className="text-[#FFB547]">fresh labels</span> while the <span className="text-[#48D8FF]">GPUs train</span>, then both GPUs fine-tune one model together.
            </div>
          </div>
        </Reveal>
      </div>
    </SlideFrame>
  );
}
