"use client";
import { Wind, Trees, Droplets, Mountain, Flame, Layers } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { SimulatorReplay } from "@/components/scientific/SimulatorReplay";
import { AwaitingResults } from "@/components/presentation/AwaitingResults";
import { formatNumber } from "@/lib/format";
import type { SlideProps } from "./slideTypes";

const inputLayers = [
  { Icon: Flame, label: "Initial burned area" },
  { Icon: Wind, label: "Wind speed & direction" },
  { Icon: Trees, label: "Fuel characteristics" },
  { Icon: Droplets, label: "Fuel moisture" },
  { Icon: Mountain, label: "Terrain & slope" },
];

export function Slide06PhysicsEngine({ isActive, reducedMotion, data, isPreview }: SlideProps) {
  const simulator = data.snapshot.simulator;
  return (
    <SlideFrame
      sceneNumber={6}
      kicker="The physics engine"
      headline={<>First, we let <span className="emberText">physics teach.</span></>}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full gap-12">
        <div className="flex w-[520px] flex-col gap-6">
          {simulator ? (
            <div className="glassPanel rounded-2xl p-6">
              <div className="fontMono text-[14px] uppercase tracking-[0.2em] text-ember">Simulator</div>
              <div className="fontDisplay mt-1 text-[34px] font-semibold text-ink">{simulator.name}</div>
              <p className="mt-2 text-[18px] leading-snug text-mute">{simulator.description}</p>
              <dl className="fontMono mt-4 grid grid-cols-2 gap-y-1 text-[16px]">
                <dt className="text-mute">Grid</dt><dd>{formatNumber(simulator.gridWidth, 0)} × {formatNumber(simulator.gridHeight, 0)}</dd>
                <dt className="text-mute">Cell size</dt><dd>{simulator.cellSizeMeters ? `${simulator.cellSizeMeters} m` : "—"}</dd>
                <dt className="text-mute">Horizon</dt><dd>{formatNumber(simulator.horizonSteps, 0)} steps</dd>
                <dt className="text-mute">Source</dt><dd className="truncate">{simulator.sourceFiles.join(", ") || "—"}</dd>
              </dl>
            </div>
          ) : (
            <AwaitingResults compact title="Simulator identity not yet ingested" artifact="snapshot.simulator" note="Name it exactly: ForeFire, or a simplified simulator labeled as such." />
          )}
          <div className="glassPanel rounded-2xl p-6">
            <div className="fontMono mb-3 flex items-center gap-2 text-[14px] uppercase tracking-[0.2em] text-mute"><Layers size={16} /> Environmental inputs</div>
            <ul className="space-y-2.5">
              {inputLayers.map(({ Icon, label }) => (
                <li key={label} className="flex items-center gap-3 text-[20px] text-ink/90"><Icon size={20} className="text-ember" /> {label}</li>
              ))}
            </ul>
            <div className="fontMono mt-4 border-t border-white/10 pt-3 text-[16px] text-mute">output → burned-area masks through simulation time</div>
          </div>
        </div>
        <SimulatorReplay simulator={simulator} isFixture={data.isFixture} width={1160} height={566} active={isActive && !isPreview} reducedMotion={reducedMotion} />
      </div>
    </SlideFrame>
  );
}
