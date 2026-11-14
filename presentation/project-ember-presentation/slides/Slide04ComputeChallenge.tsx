"use client";
import { motion } from "framer-motion";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { JobQueueField } from "@/components/visualizations/JobQueueField";
import { useSceneClock } from "@/hooks/useSceneClock";
import type { SlideProps } from "./slideTypes";

export function Slide04ComputeChallenge({ step, isActive, isPreview, reducedMotion }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 9, maxFps: 30 });
  // Freeze the queue once the question appears so attention moves to it.
  const queueTime = Math.min(time, 16);

  return (
    <SlideFrame
      sceneNumber={4}
      kicker="The computational challenge"
      headline={<>The more we ask, <span className="emberText">the more we compute.</span></>}
      lede="Every new set of conditions is another independent simulation job."
      reducedMotion={reducedMotion}
    >
      <div className="relative h-full">
        <motion.div initial={false} animate={{ opacity: step >= 1 ? 0.18 : 1, filter: step >= 1 ? "blur(3px)" : "blur(0px)" }} transition={{ duration: reducedMotion ? 0 : 0.6 }}>
          <JobQueueField time={queueTime} width={1728} height={620} />
        </motion.div>
        <motion.div
          className="absolute inset-0 flex flex-col items-center justify-center text-center"
          initial={false}
          animate={{ opacity: step >= 1 ? 1 : 0, scale: step >= 1 ? 1 : 0.96 }}
          transition={{ duration: reducedMotion ? 0 : 0.7 }}
        >
          <div className="fontDisplay text-[92px] font-bold leading-[1.02] text-ink">
            What if the physics
            <br />
            could be <span className="cyanText">approximated?</span>
          </div>
        </motion.div>
        <div className="absolute bottom-0 left-0">
          <EvidenceBadge kind="illustration" detail="normalized units · no timings claimed" />
        </div>
      </div>
    </SlideFrame>
  );
}
