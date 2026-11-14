"use client";
import { useEffect, useMemo, useState } from "react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { AwaitingResults } from "@/components/presentation/AwaitingResults";
import { ComparisonTriptych, DifferenceLegend, useDecodedExample } from "@/components/scientific/ComparisonTriptych";
import { MetricStat } from "@/components/charts/MetricStat";
import { formatSignedPercent } from "@/lib/format";
import type { SlideProps } from "./slideTypes";

const fixed3 = (v: number) => v.toFixed(3);

export function Slide11MomentOfTruth({ isActive, reducedMotion, data }: SlideProps) {
  const fidelity = data.snapshot.fidelity;
  const examples = fidelity?.examples ?? [];
  const [selected, setSelected] = useState(0);
  useEffect(() => {
    if (!isActive) setSelected(0);
  }, [isActive]);

  const example = examples[selected] ?? null;
  const decoded = useDecodedExample(example);
  const exampleMetrics = decoded?.agreement ?? example?.metrics ?? null;
  const weakestIndex = useMemo(() => {
    let worst = -1;
    let worstIou = Infinity;
    examples.forEach((ex, k) => {
      const iou = ex.metrics?.iou;
      if (typeof iou === "number" && iou < worstIou) {
        worstIou = iou;
        worst = k;
      }
    });
    return worst;
  }, [examples]);

  return (
    <SlideFrame
      sceneNumber={11}
      kicker="The moment of truth"
      headline={<>How close did <span className="cyanText">AI</span> get?</>}
      accent="#48D8FF"
      aside={fidelity ? <EvidenceBadge kind={data.evidenceFor("fidelity")} isFixture={data.isFixture} detail={fidelity.source.path} /> : undefined}
      reducedMotion={reducedMotion}
    >
      {!fidelity ? (
        <div className="flex h-full flex-col gap-6">
          <div className="grid flex-1 grid-cols-3 gap-6">
            {["Simulator reference", "Surrogate prediction", "Difference / error map"].map((title, k) => (
              <div key={title} className="flex flex-col">
                <div className="fontMono mb-2 text-[16px] uppercase tracking-[0.16em]" style={{ color: ["#FF6B35", "#48D8FF", "#94A3B8"][k] }}>{title}</div>
                <AwaitingResults compact className="flex-1" title="Awaiting held-out outputs" artifact={k === 2 ? "computed from reference + prediction" : "metrics/results.json → examples[]"} />
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between">
            <div className="fontMono text-[17px] text-mute">IoU · precision · recall · F2 · burned-area error will appear from the evaluation artifact.</div>
            <div className="fontDisplay text-[22px] text-ink/85">Surrogate fidelity relative to held-out simulated states.</div>
          </div>
        </div>
      ) : (
        <div className="flex h-full gap-10">
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-2">
              {examples.map((ex, k) => (
                <button
                  key={ex.id}
                  onClick={() => setSelected(k)}
                  className={`fontMono rounded-lg border px-3 py-2 text-[15px] transition ${k === selected ? "border-[#48D8FF] bg-[#48D8FF]/15 text-ink" : "border-white/10 text-mute hover:text-ink"}`}
                >
                  {ex.label}
                  {k === weakestIndex ? <span className="ml-2 rounded bg-ember/20 px-1.5 text-[12px] text-ember">weakest</span> : null}
                </button>
              ))}
            </div>
            {example ? <ComparisonTriptych example={example} panelSize={420} /> : null}
            <div className="flex items-center justify-between">
              <DifferenceLegend />
              <span className="fontMono text-[14px] text-mute">horizon {example?.horizon ?? fidelity.horizon ?? "—"}</span>
            </div>
          </div>
          <div className="flex w-[330px] flex-col gap-5">
            <div className="glassPanel rounded-2xl p-5">
              <div className="fontMono mb-2 text-[13px] uppercase tracking-[0.2em] text-[#48D8FF]">Held-out {fidelity.split} · n = {fidelity.sampleCount ?? "—"}</div>
              <MetricStat label="Mean fire-mask IoU" value={fidelity.aggregate.iou} format={fixed3} active={isActive} reducedMotion={reducedMotion} size="lg" color="#48D8FF" />
              <div className="mt-3 grid grid-cols-2 gap-4">
                <MetricStat label="Precision" value={fidelity.aggregate.precision} format={fixed3} active={isActive} reducedMotion={reducedMotion} size="sm" />
                <MetricStat label="Recall" value={fidelity.aggregate.recall} format={fixed3} active={isActive} reducedMotion={reducedMotion} size="sm" />
                <MetricStat label="F2" value={fidelity.aggregate.f2} format={fixed3} active={isActive} reducedMotion={reducedMotion} size="sm" />
                <MetricStat label="Area error" value={fidelity.aggregate.burnedAreaError} format={(v) => formatSignedPercent(v)} active={isActive} reducedMotion={reducedMotion} size="sm" />
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 p-5">
              <div className="fontMono mb-2 text-[13px] uppercase tracking-[0.2em] text-mute">This example{decoded ? " · recomputed from masks" : ""}</div>
              <div className="grid grid-cols-2 gap-3">
                <MetricStat label="IoU" value={exampleMetrics?.iou ?? null} format={fixed3} active={isActive} reducedMotion size="sm" />
                <MetricStat label="Area error" value={exampleMetrics?.burnedAreaError ?? null} format={(v) => formatSignedPercent(v)} active={isActive} reducedMotion size="sm" />
              </div>
            </div>
            {fidelity.baselines?.length ? (
              <div className="fontMono text-[14px] text-mute">
                Baseline · {fidelity.baselines[0].name}: IoU {fidelity.baselines[0].metrics.iou?.toFixed(3) ?? "—"}
              </div>
            ) : null}
          </div>
        </div>
      )}
      {fidelity ? (
        <div className="absolute bottom-0 left-0 right-0 flex items-end justify-between">
          <div className="fontDisplay text-[22px] text-ink/90">“Surrogate fidelity relative to held-out simulated states.”</div>
          <div className="max-w-[640px] text-right text-[15px] text-mute">Agreement with simulator outputs is not real-world wildfire forecast accuracy.</div>
        </div>
      ) : null}
    </SlideFrame>
  );
}
