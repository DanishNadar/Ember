"use client";
import { useMemo } from "react";
import { Wind, Droplets, Home } from "lucide-react";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { FireCanvas } from "@/components/visualizations/FireCanvas";
import { simulateFireSpread, type FireScenarioParams } from "@/lib/fireModel";
import { useSceneClock } from "@/hooks/useSceneClock";
import type { SlideProps } from "./slideTypes";

const base: FireScenarioParams = { width: 192, height: 108, terrainSeed: 2024, windDirectionDeg: 90, windSpeed: 4, fuelMoisture: 0.12, ignitions: [[86, 58]] };

const conditionPresets = [
  { label: "Light westerly breeze", windDirectionDeg: 90, windSpeed: 3, fuelMoisture: 0.14 },
  { label: "Strong southerly wind", windDirectionDeg: 0, windSpeed: 13, fuelMoisture: 0.08 },
  { label: "Dry north-easterly gusts", windDirectionDeg: 225, windSpeed: 10, fuelMoisture: 0.04 },
  { label: "Humid and calm", windDirectionDeg: 120, windSpeed: 1.5, fuelMoisture: 0.3 },
];

/** Illustrative structures placed on the landscape (grid coordinates). */
const structures: Array<[number, number]> = [
  [120, 40], [126, 44], [131, 38], [64, 30], [70, 26], [60, 82], [104, 86], [110, 90], [146, 66], [150, 60], [40, 56], [88, 18],
];

const cycleSeconds = 4.2;
const panelWidth = 1000;
const panelHeight = 562;

export function Slide02HumanProblem({ step, isActive, isPreview, reducedMotion }: SlideProps) {
  const runs = useMemo(() => conditionPresets.map((p) => simulateFireSpread({ ...base, ...p })), []);
  const horizon = useMemo(() => runs[0].maxArrival * 0.3, [runs]);
  const time = useSceneClock({ isActive, isPreview, reducedMotion, settledTime: cycleSeconds * 1 + 3.6 });

  const presetIndex = Math.floor(time / cycleSeconds) % conditionPresets.length;
  const local = time % cycleSeconds;
  const modelTime = horizon * Math.min(1, local / 3.0);
  const run = runs[presetIndex];
  const preset = conditionPresets[presetIndex];

  const scaleX = panelWidth / base.width;
  const scaleY = panelHeight / base.height;

  return (
    <SlideFrame
      sceneNumber={2}
      kicker="The human problem"
      headline={<>Wildfire doesn&apos;t follow <span className="emberText">one future.</span></>}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full gap-14">
        <div className="flex w-[560px] flex-col justify-between pb-4">
          <div className="space-y-7 text-[25px] leading-snug text-mute">
            <p>Fires threaten <span className="text-ink">ecosystems, communities, infrastructure</span> and livelihoods.</p>
            <p>The same ignition, under different wind and fuel moisture, can lead to <span className="text-ink">very different simulated outcomes.</span></p>
            <p>Each change in conditions is a new question, and each question needs another run.</p>
          </div>
          <Reveal show={step >= 1} reducedMotion={reducedMotion}>
            <div className="border-l-4 border-ember pl-6">
              <div className="fontDisplay text-[40px] font-semibold leading-tight text-ink">
                “When conditions change,
                <br />
                the questions <span className="emberText">multiply.</span>”
              </div>
            </div>
          </Reveal>
        </div>

        <div className="flex flex-col gap-4">
          <div className="relative overflow-hidden rounded-2xl border border-white/10" style={{ width: panelWidth, height: panelHeight }}>
            <FireCanvas run={run} time={modelTime} width={panelWidth} height={panelHeight} sparks={isActive && !reducedMotion} windArrows options={{ burnDuration: 36 }} ariaLabel={`Illustrative spread under ${preset.label}`} />
            <svg className="pointer-events-none absolute inset-0" width={panelWidth} height={panelHeight}>
              {structures.map(([x, y]) => {
                const burned = run.arrival[y * base.width + x] <= modelTime;
                return (
                  <g key={`${x}-${y}`} transform={`translate(${x * scaleX - 9}, ${y * scaleY - 9})`}>
                    <rect width="18" height="18" rx="3" fill={burned ? "#E53935" : "#F3F6FA"} opacity={burned ? 0.95 : 0.85} />
                    <path d="M3 9 L9 3 L15 9 V15 H3 Z" fill={burned ? "#FFE3B0" : "#080B10"} />
                  </g>
                );
              })}
            </svg>
            <div className="glassPanel absolute left-5 top-5 rounded-xl px-5 py-4">
              <div className="fontMono text-[13px] uppercase tracking-[0.2em] text-mute">Condition set {presetIndex + 1} / 4</div>
              <div className="fontDisplay mt-1 text-[24px] font-semibold text-ink">{preset.label}</div>
              <div className="fontMono mt-2 flex gap-5 text-[16px] text-[#48D8FF]">
                <span className="flex items-center gap-1.5"><Wind size={16} /> {preset.windSpeed} m/s → {preset.windDirectionDeg}°</span>
                <span className="flex items-center gap-1.5 text-mute"><Droplets size={16} /> {Math.round(preset.fuelMoisture * 100)}% fuel moisture</span>
              </div>
            </div>
            <div className="absolute bottom-4 left-5"><EvidenceBadge kind="illustration" detail="toy model; not a forecast" /></div>
            <div className="fontMono absolute bottom-5 right-5 flex items-center gap-2 text-[14px] text-mute"><Home size={15} /> illustrative structures</div>
          </div>
          <div className="flex gap-3">
            {runs.map((r, k) => (
              <div key={k} className={`overflow-hidden rounded-lg border transition ${k === presetIndex ? "border-ember" : "border-white/10 opacity-60"}`}>
                <FireCanvas run={r} time={horizon} width={238} height={134} bloom={false} options={{ showContours: false }} resolution={1} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </SlideFrame>
  );
}
