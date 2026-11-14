"use client";
import { SparkSequence, sparkTimeline } from "@/components/visualizations/SparkSequence";
import { EmberWordmark } from "@/components/visualizations/EmberLogo";
import { Reveal } from "@/components/presentation/Reveal";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { useSceneClock } from "@/hooks/useSceneClock";
import { FuzzballMark, PartnerStrip } from "@/components/visualizations/BrandMarks";
import { fuzzballGreen } from "@/lib/ecosystem";
import type { SlideProps } from "./slideTypes";

export function Slide01Spark({ isActive, isPreview, reducedMotion }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: sparkTimeline.settled });

  return (
    <div className="absolute inset-0">
      <SparkSequence time={time} />
      {/* Readability gradient for the text column */}
      <div className="pointer-events-none absolute inset-0" style={{ background: "linear-gradient(90deg, rgba(8,11,16,0.94) 0%, rgba(8,11,16,0.78) 36%, rgba(8,11,16,0) 62%)" }} />
      <div className="absolute left-[110px] top-[150px] w-[900px]">
        <Reveal show={time > 2.2} reducedMotion={reducedMotion}>
          <div className="fontMono mb-6 whitespace-nowrap text-[17px] uppercase tracking-[0.24em] text-mute">CIQ Supercomputing Local AI Hackathon · Chicago · Nov 13–15, 2026</div>
        </Reveal>
        <Reveal show={time > 2.9} reducedMotion={reducedMotion}>
          <h1 className="fontDisplay text-[96px] font-bold leading-[0.98] text-ink">
            ONE SPARK.
            <br />
            <span className="emberText">THOUSANDS</span> OF
            <br />
            POSSIBLE FUTURES.
          </h1>
        </Reveal>
        <Reveal show={time > 6.2} reducedMotion={reducedMotion} className="mt-16">
          <EmberWordmark scale={0.9} />
        </Reveal>
        <Reveal show={time > 7.2} reducedMotion={reducedMotion} className="mt-8">
          <div className="fontDisplay text-[34px] font-medium text-ink/90">From Simulating One Future to Exploring Thousands.</div>
        </Reveal>
      </div>
      <Reveal show={time > 7.6} reducedMotion={reducedMotion} className="absolute right-[90px] top-[86px] flex flex-col items-end gap-4">
        <div className="glassPanel flex items-center gap-4 rounded-2xl px-5 py-3">
          <span className="fontMono text-[14px] uppercase tracking-[0.2em] text-mute">Orchestrated with</span>
          <FuzzballMark size={40} />
          <span className="fontDisplay text-[30px] font-semibold text-ink">Fuzzball</span>
          <span className="fontMono text-[14px] tracking-[0.12em]" style={{ color: fuzzballGreen }}>on 2 × NVIDIA GB10</span>
        </div>
        <PartnerStrip height={44} className="opacity-85" />
      </Reveal>
      <Reveal show={time > 5.2} reducedMotion={reducedMotion} className="absolute bottom-[56px] left-[110px] flex items-center gap-4">
        <EvidenceBadge kind="illustration" detail="deck's toy spread model, not simulator output" />
        <span className="fontMono flex items-center gap-2 text-[15px] text-[#48D8FF]"><span className="inline-block h-[3px] w-6 bg-[#48D8FF]" /> alternative futures</span>
      </Reveal>
    </div>
  );
}
