"use client";
import { useEffect, useState } from "react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { ArchitectureDiagram } from "@/components/visualizations/ArchitectureDiagram";
import { useSceneClock } from "@/hooks/useSceneClock";
import type { ArchitectureComponent } from "@/lib/architecture";
import type { SlideProps } from "./slideTypes";

export function Slide05MeetEmber({ isActive, isPreview, reducedMotion, data }: SlideProps) {
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 10, maxFps: 20 });
  const revealed = Math.min(6, Math.floor(time / 0.45) + 1);
  const [selectedId, setSelectedId] = useState<ArchitectureComponent["id"] | null>(null);

  useEffect(() => {
    if (!isActive) setSelectedId(null);
  }, [isActive]);

  return (
    <SlideFrame
      sceneNumber={5}
      kicker="Introducing Ember"
      headline={<>Meet <span className="emberText">Project Ember.</span></>}
      lede="Physics teaches. AI learns. Fuzzball coordinates. We explore."
      aside={<EvidenceBadge kind="illustration" detail="planned architecture · status from snapshot" />}
      reducedMotion={reducedMotion}
    >
      <ArchitectureDiagram selectedId={selectedId} onSelect={setSelectedId} revealed={revealed} data={data} reducedMotion={reducedMotion} />
    </SlideFrame>
  );
}
