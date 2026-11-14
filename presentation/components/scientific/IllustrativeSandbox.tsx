"use client";
/** "What-if" sandbox driven by the deck's toy model. Output is always labeled illustrative. */
import { useMemo, useState } from "react";
import { FireCanvas } from "@/components/visualizations/FireCanvas";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { baseScenario, simulateFireSpread } from "@/lib/fireModel";

function Slider({ label, value, min, max, step, unit, onChange }: { label: string; value: number; min: number; max: number; step: number; unit: string; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <div className="fontMono mb-1 flex justify-between text-[14px] text-mute"><span>{label}</span><span className="text-ink">{value}{unit}</span></div>
      <input type="range" className="emberRange w-full" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} aria-label={label} />
    </label>
  );
}

export function IllustrativeSandbox() {
  const [windDirectionDeg, setWindDirection] = useState(70);
  const [windSpeed, setWindSpeed] = useState(7);
  const [moisture, setMoisture] = useState(12);
  const [horizon, setHorizon] = useState(30);
  const run = useMemo(() => simulateFireSpread({ ...baseScenario, windDirectionDeg, windSpeed, fuelMoisture: moisture / 100 }), [windDirectionDeg, windSpeed, moisture]);
  const reference = useMemo(() => simulateFireSpread(baseScenario), []);
  const time = reference.maxArrival * (horizon / 100);

  return (
    <div className="flex flex-wrap gap-6">
      <div className="relative overflow-hidden rounded-xl border border-white/10">
        <FireCanvas run={run} time={time} width={800} height={450} windArrows options={{ burnDuration: 30, isochroneStep: reference.maxArrival / 20 }} resolution={1} />
        <div className="absolute left-3 top-3"><EvidenceBadge kind="illustration" detail="toy model · not ForeFire · not the surrogate" /></div>
      </div>
      <div className="flex w-[300px] flex-col gap-5">
        <Slider label="Wind direction (toward)" value={windDirectionDeg} min={0} max={359} step={1} unit="°" onChange={setWindDirection} />
        <Slider label="Wind speed" value={windSpeed} min={0} max={20} step={0.5} unit=" m/s" onChange={setWindSpeed} />
        <Slider label="Fuel moisture" value={moisture} min={2} max={40} step={1} unit="%" onChange={setMoisture} />
        <Slider label="Horizon" value={horizon} min={2} max={80} step={1} unit="%" onChange={setHorizon} />
        <p className="text-[14px] leading-snug text-mute">
          A deterministic minimum-travel-time toy model for intuition only. It is not the project&apos;s simulator or neural surrogate, and its outputs are not results.
        </p>
      </div>
    </div>
  );
}
