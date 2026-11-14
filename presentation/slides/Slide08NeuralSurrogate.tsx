"use client";
import { useState } from "react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { AwaitingResults } from "@/components/presentation/AwaitingResults";
import { UNetDiagram } from "@/components/visualizations/UNetDiagram";
import { ComparisonTriptych } from "@/components/scientific/ComparisonTriptych";
import { useSceneClock } from "@/hooks/useSceneClock";
import { formatCount, formatNumber, formatSeconds } from "@/lib/format";
import { SegmentedToggle } from "@/components/controls/SegmentedToggle";
import type { SlideProps } from "./slideTypes";



export function Slide08NeuralSurrogate({ isActive, isPreview, reducedMotion, data }: SlideProps) {
  const [view, setView] = useState<"architecture" | "prediction">("architecture");
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: 1.4, maxFps: 30 });
  const model = data.snapshot.model;
  const example = data.snapshot.fidelity?.examples[0] ?? null;

  const specRows: Array<[string, string]> = model
    ? [
        ["Model type", model.modelType],
        ["Parameters", formatCount(model.parameterCount)],
        ["Input", model.inputResolution ?? "—"],
        ["Output", model.outputResolution ?? "—"],
        ["Epochs", formatNumber(model.training.epochs, 0)],
        ["Batch size", formatNumber(model.training.batchSize, 0)],
        ["Optimizer", model.training.optimizer ?? "—"],
        ["Learning rate", model.training.learningRate !== null ? String(model.training.learningRate) : "—"],
        ["Loss", model.training.loss ?? "—"],
        ["Training time", formatSeconds(model.training.wallClockSeconds)],
        ["Device", model.device ?? "—"],
      ]
    : [];

  return (
    <SlideFrame
      sceneNumber={8}
      kicker="The neural surrogate"
      headline={<>Then, <span className="cyanText">AI learns the pattern.</span></>}
      accent="#48D8FF"
      aside={<SegmentedToggle options={[["architecture", "Architecture view"], ["prediction", "Prediction view"]]} value={view} onChange={setView} />}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full gap-10">
        <div className="glassPanel relative flex-1 rounded-2xl p-6">
          {view === "architecture" ? (
            <>
              <UNetDiagram width={1180} height={560} time={time} reducedMotion={reducedMotion} />
              <div className="mt-3 grid grid-cols-3 gap-6 text-[18px] leading-snug text-mute">
                <p><span className="text-[#48D8FF]">Encoder</span> compresses spatial context: where the front is and what drives it.</p>
                <p><span className="text-[#48D8FF]">Skip connections</span> carry fine detail so the front edge stays sharp.</p>
                <p><span className="text-[#48D8FF]">Decoder</span> rebuilds a full-resolution burned-area prediction.</p>
              </div>
              <div className="absolute right-5 top-5"><EvidenceBadge kind="illustration" detail="schematic" /></div>
            </>
          ) : example ? (
            <div className="flex h-full flex-col justify-center gap-4">
              <ComparisonTriptych example={example} panelSize={340} />
              <div className="flex items-center justify-between">
                <span className="fontMono text-[16px] text-mute">held-out example {example.id} · {example.label}</span>
                <EvidenceBadge kind={data.evidenceFor("fidelity")} isFixture={data.isFixture} detail={data.snapshot.fidelity?.source.path} />
              </div>
            </div>
          ) : (
            <AwaitingResults className="h-full" artifact="metrics/results.json → examples[]" note="Prediction view shows real surrogate outputs on held-out scenarios once ingested." />
          )}
        </div>
        <div className="glassPanel w-[440px] rounded-2xl p-6">
          <div className="fontMono mb-4 flex items-center justify-between text-[14px] uppercase tracking-[0.2em] text-[#48D8FF]">
            Model card
            {model ? <EvidenceBadge kind={data.evidenceFor("model")} isFixture={data.isFixture} /> : null}
          </div>
          {model ? (
            <>
              <dl className="fontMono grid grid-cols-[150px_1fr] gap-y-2.5 text-[17px]">
                {specRows.map(([k, v]) => (
                  <div key={k} className="contents"><dt className="text-mute">{k}</dt><dd className="text-ink">{v}</dd></div>
                ))}
              </dl>
              <div className="fontMono mt-5 border-t border-white/10 pt-3 text-[13px] text-mute">
                {model.definitionFile ?? "definition: —"} · {model.checkpoint ?? "checkpoint: —"}
                <br />source: {model.source.path}
              </div>
            </>
          ) : (
            <AwaitingResults compact title="Model metadata awaiting" artifact="models/metadata.json + best.pt" note="Type, parameter count, resolution, training config and device are read from artifacts, never typed in." />
          )}
        </div>
      </div>
    </SlideFrame>
  );
}
