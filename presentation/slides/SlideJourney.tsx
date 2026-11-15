"use client";
import { CircleCheck, CircleX, Wrench } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { useSceneClock } from "@/hooks/useSceneClock";
import { milestones, struggles } from "@/data/verified/measuredResults";
import type { SlideProps } from "./slideTypes";

export function SlideJourney({ isActive, isPreview, reducedMotion }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 5, maxFps: 20 });

  return (
    <SlideFrame
      kicker="The process"
      headline={<>What broke, <span className="emberText">and how we fixed it.</span></>}
      aside={<EvidenceBadge kind="verified" detail="test runs · Nov 15" />}
      reducedMotion={reducedMotion}
      showFooter={false}
    >
      <div className="flex h-full flex-col gap-8">
        {/* Milestone track, failures included */}
        <div className="relative grid grid-cols-4 gap-5">
          <div className="absolute left-[12%] right-[12%] top-[22px] h-[2px] bg-gradient-to-r from-[#FF6B35] via-[#FFB547] to-[#35D6A0] opacity-50" />
          {milestones.map((m, k) => (
            <Reveal key={m.run} show={time > 0.3 + k * 0.45} reducedMotion={reducedMotion} className="relative flex flex-col items-center text-center">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-void">
                {m.ok ? <CircleCheck size={40} className="text-[#35D6A0]" /> : <CircleX size={40} className="text-[#E53935]" />}
              </div>
              <div className="fontMono mt-2 text-[15px] text-mute">run {m.run}</div>
              <div className={`mt-1 max-w-[340px] text-[20px] leading-snug ${m.ok ? "text-ink" : "text-[#FF8A80]"}`}>{m.label}</div>
            </Reveal>
          ))}
        </div>

        {/* Struggles → fixes */}
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-5">
          {struggles.map((s, k) => (
            <Reveal key={s.problem} show={time > 2.2 + k * 0.35} reducedMotion={reducedMotion}>
              <div className="glassPanel h-full rounded-2xl p-6">
                <div className="fontDisplay text-[25px] font-semibold text-ink">{s.problem}</div>
                <div className="mt-2 flex items-start gap-3 text-[20px] leading-snug text-mute">
                  <Wrench size={20} className="mt-1 shrink-0 text-[#35D6A0]" />
                  <span>{s.fix}</span>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </SlideFrame>
  );
}
