"use client";
import { useEffect, useState } from "react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EnsembleExplorer, type EnsembleView } from "@/components/scientific/EnsembleExplorer";
import type { SlideProps } from "./slideTypes";

const viewForStep: EnsembleView[] = ["single", "many", "agreement"];

export function Slide13ComputeUnlocks({ step, reducedMotion, data }: SlideProps) {
  const [view, setView] = useState<EnsembleView>(viewForStep[step] ?? "single");
  useEffect(() => setView(viewForStep[Math.min(step, 2)]), [step]);
  const recorded = data.snapshot.ensemble !== null;

  return (
    <SlideFrame
      sceneNumber={13}
      kicker={recorded ? "What additional compute unlocks" : "What additional compute unlocks · proposed extension"}
      headline={<>More compute. <span className="emberText">More questions we can ask.</span></>}
      reducedMotion={reducedMotion}
    >
      <EnsembleExplorer ensemble={data.snapshot.ensemble} isFixture={data.isFixture} view={view} onViewChange={setView} width={1290} height={620} showSummary={step >= 2 || view === "agreement"} />
    </SlideFrame>
  );
}
