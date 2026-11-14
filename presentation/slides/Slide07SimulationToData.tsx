"use client";
import { useMemo } from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { AwaitingResults } from "@/components/presentation/AwaitingResults";
import { Reveal } from "@/components/presentation/Reveal";
import { FireCanvas } from "@/components/visualizations/FireCanvas";
import { ChannelTile, type ChannelSpec } from "@/components/scientific/ChannelTile";
import { baseScenario, burnedMaskAt, simulateFireSpread } from "@/lib/fireModel";
import { decodeRowMask } from "@/lib/maskMetrics";
import { formatCount } from "@/lib/format";
import type { SlideProps } from "./slideTypes";

const tileW = 228;
const tileH = 128;

export function Slide07SimulationToData({ step, reducedMotion, data }: SlideProps) {
  const dataset = data.snapshot.dataset;
  const sample = dataset?.samples?.[0] ?? null;

  const illustrative = useMemo(() => {
    const run = simulateFireSpread(baseScenario);
    const t0 = run.maxArrival * 0.14;
    const t1 = run.maxArrival * 0.28;
    const size = run.arrival.length;
    const rad = (baseScenario.windDirectionDeg * Math.PI) / 180;
    const u = (Math.sin(rad) * baseScenario.windSpeed) / 20 + 0.5;
    const v = (-Math.cos(rad) * baseScenario.windSpeed) / 20 + 0.5;
    const channels: ChannelSpec[] = [
      { kind: "mask", name: "burned mask (t)", mask: burnedMaskAt(run, t0) },
      { kind: "scalar", name: "wind U", values: new Float32Array(size).fill(u), arrowDeg: baseScenario.windDirectionDeg },
      { kind: "scalar", name: "wind V", values: new Float32Array(size).fill(v), arrowDeg: baseScenario.windDirectionDeg },
      { kind: "scalar", name: "fuel", values: run.terrain.fuel },
      { kind: "scalar", name: "moisture", values: new Float32Array(size).fill(baseScenario.fuelMoisture * 2) },
      { kind: "scalar", name: "slope", values: Array.from(run.terrain.slope, (s) => Math.min(1, s * 1.4)) },
    ];
    return { run, t0, channels, target: burnedMaskAt(run, t1), width: run.terrain.width, height: run.terrain.height };
  }, []);

  const real = useMemo(() => {
    if (!sample) return null;
    const target = decodeRowMask(sample.target);
    const channels: ChannelSpec[] = Object.entries(sample.channels).map(([name, rows]) => {
      const decoded = decodeRowMask(rows);
      return { kind: "mask", name, mask: decoded.mask, color: name.toLowerCase().includes("burn") ? [255, 107, 53] : [148, 163, 184] } as ChannelSpec;
    });
    return { channels, target: target.mask, width: target.width, height: target.height };
  }, [sample]);

  const view = real ?? illustrative;
  const splits = dataset?.splits;
  const total = splits ? (splits.train ?? 0) + (splits.validation ?? 0) + (splits.test ?? 0) : 0;

  return (
    <SlideFrame
      sceneNumber={7}
      kicker="From simulation to data"
      headline={<>Every simulation becomes <span className="emberText">a lesson.</span></>}
      aside={<EvidenceBadge kind={real ? data.evidenceFor("dataset") : "illustration"} isFixture={data.isFixture} detail={real ? `sample ${sample?.id}` : "thumbnails illustrative"} />}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full flex-col gap-8">
        <div className="flex items-center gap-8">
          <div className="flex flex-col gap-2">
            <div className="overflow-hidden rounded-xl border border-ember/40" style={{ width: 400, height: 225 }}>
              <FireCanvas run={illustrative.run} time={illustrative.t0} width={400} height={225} options={{ burnDuration: 30 }} resolution={1} />
            </div>
            <div className="fontMono text-[15px] text-mute">simulation snapshot · t</div>
          </div>
          <ArrowRight size={36} className="shrink-0 text-ember" />
          <div className="relative" style={{ width: 3 * tileW + 2 * 18, height: 2 * (tileH + 30) + 18 }}>
            {view.channels.slice(0, 6).map((spec, k) => {
              const col = k % 3;
              const row = Math.floor(k / 3);
              const spread = step >= 1;
              return (
                <motion.div
                  key={spec.name}
                  className="absolute left-0 top-0"
                  initial={false}
                  animate={{
                    x: spread ? col * (tileW + 18) : k * 10,
                    y: spread ? row * (tileH + 48) : 60 + k * 8,
                    opacity: spread ? 1 : 0.35 + k * 0.1,
                  }}
                  transition={{ duration: reducedMotion ? 0 : 0.7, delay: spread && !reducedMotion ? k * 0.06 : 0, ease: [0.2, 0.7, 0.2, 1] }}
                >
                  <ChannelTile spec={spec} gridWidth={view.width} gridHeight={view.height} width={tileW} height={tileH} />
                </motion.div>
              );
            })}
          </div>
          <Reveal show={step >= 1} delay={0.4} reducedMotion={reducedMotion} className="flex items-center gap-8">
            <div className="flex flex-col items-center">
              <ArrowRight size={36} className="text-[#48D8FF]" />
              <span className="fontMono mt-1 text-[13px] text-mute">learn</span>
            </div>
            <ChannelTile spec={{ kind: "mask", name: "target: burned mask (t + h)", mask: view.target, color: [255, 181, 71] }} gridWidth={view.width} gridHeight={view.height} width={300} height={169} />
          </Reveal>
        </div>

        <Reveal show={step >= 2} reducedMotion={reducedMotion} className="glassPanel rounded-2xl p-6">
          {dataset && total > 0 && splits ? (
            <div className="flex items-center gap-10">
              <div className="w-[300px]">
                <div className="fontMono text-[14px] uppercase tracking-[0.2em] text-mute">Dataset · split by {dataset.splitUnit}</div>
                <div className="fontMono mt-1 text-[40px] font-semibold text-ink">{formatCount(dataset.totalScenarios)} <span className="text-[20px] text-mute">scenarios</span></div>
                <div className="fontMono text-[16px] text-mute">{formatCount(dataset.totalExamples)} examples · {dataset.inputChannels.length} input channels</div>
              </div>
              <div className="flex-1">
                <div className="flex h-12 overflow-hidden rounded-lg">
                  {([["train", splits.train, "#FF6B35"], ["validation", splits.validation, "#FFB547"], ["test", splits.test, "#48D8FF"]] as const).map(([name, count, color]) => (
                    <motion.div key={name} initial={false} animate={{ width: `${((count ?? 0) / total) * 100}%` }} transition={{ duration: reducedMotion ? 0 : 0.9 }} style={{ background: color }} className="fontMono flex items-center justify-center text-[16px] font-semibold text-black">
                      {count}
                    </motion.div>
                  ))}
                </div>
                <div className="fontMono mt-2 flex gap-8 text-[15px] text-mute">
                  <span><span className="text-ember">■</span> train</span><span><span className="text-[#FFB547]">■</span> validation</span><span><span className="text-[#48D8FF]">■</span> held-out test (never seen in training)</span>
                  <span className="ml-auto">source: {dataset.source.path}</span>
                </div>
              </div>
            </div>
          ) : (
            <AwaitingResults compact title="Dataset split awaiting manifest" artifact="data/manifest.json" note="Scenarios will be partitioned into train / validation / test by scenario so held-out tests stay unseen." />
          )}
        </Reveal>
      </div>
    </SlideFrame>
  );
}
