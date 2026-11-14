"use client";
import { useMemo } from "react";
import { motion } from "framer-motion";
import { SlideFrame } from "@/components/presentation/SlideFrame";
import { Reveal } from "@/components/presentation/Reveal";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { FireCanvas } from "@/components/visualizations/FireCanvas";
import { simulateFireSpread, type FireScenarioParams } from "@/lib/fireModel";
import type { SlideProps } from "./slideTypes";

const thumbGrid: FireScenarioParams = { width: 96, height: 54, terrainSeed: 1337, windDirectionDeg: 80, windSpeed: 6, fuelMoisture: 0.1, ignitions: [[44, 28]] };
const windDirections = [35, 80, 150];
const windSpeeds = [3, 7, 12];
const moistures = [0.05, 0.12, 0.25];

const treeWidth = 1060;
const treeHeight = 640;
const levelX = [70, 330, 640, 960];

function levelYs(count: number, top = 40, bottom = treeHeight - 40) {
  if (count === 1) return [(top + bottom) / 2];
  return Array.from({ length: count }, (_, k) => top + ((bottom - top) * k) / (count - 1));
}

function branchPath(x1: number, y1: number, x2: number, y2: number) {
  const mx = (x1 + x2) / 2;
  return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
}

export function Slide03OneSimulation({ step, reducedMotion }: SlideProps) {
  const rootRun = useMemo(() => simulateFireSpread(thumbGrid), []);
  const level2Runs = useMemo(
    () => windDirections.flatMap((d) => windSpeeds.map((s) => simulateFireSpread({ ...thumbGrid, windDirectionDeg: d, windSpeed: s }))),
    [],
  );
  const horizon = rootRun.maxArrival * 0.32;
  const leafFractions = useMemo(() => {
    const coarse = { ...thumbGrid, width: 48, height: 27, ignitions: [[22, 14]] as Array<[number, number]> };
    const coarseHorizon = simulateFireSpread(coarse).maxArrival * 0.32;
    return windDirections.flatMap((d) => windSpeeds.flatMap((s) => moistures.map((m) => {
      const r = simulateFireSpread({ ...coarse, windDirectionDeg: d, windSpeed: s, fuelMoisture: m });
      let burned = 0;
      for (const a of r.arrival) if (a <= coarseHorizon) burned++;
      return burned / r.arrival.length;
    })));
  }, []);

  const y1 = levelYs(3, 110, treeHeight - 110);
  const y2 = levelYs(9, 40, treeHeight - 40);
  const y3 = levelYs(27, 22, treeHeight - 22);
  const rootY = treeHeight / 2;
  const draw = (show: boolean, delay = 0) => ({
    initial: false as const,
    animate: { pathLength: show ? 1 : 0, opacity: show ? 1 : 0 },
    transition: reducedMotion ? { duration: 0 } : { duration: 0.9, delay: show ? delay : 0, ease: "easeInOut" as const },
  });
  const runCount = step === 0 ? 1 : step === 1 ? 9 : 27;

  return (
    <SlideFrame
      sceneNumber={3}
      kicker="Why one simulation isn't enough"
      headline={<>One simulation. <span className="emberText">One set of assumptions.</span></>}
      reducedMotion={reducedMotion}
    >
      <div className="flex h-full gap-10">
        <div className="flex w-[560px] flex-col gap-6">
          <div className="glassPanel rounded-2xl p-6">
            <div className="fontMono mb-3 text-[14px] uppercase tracking-[0.2em] text-ember">Deterministic run · inputs</div>
            <div className="mb-4 overflow-hidden rounded-lg border border-white/10">
              <FireCanvas run={rootRun} time={horizon} width={510} height={287} options={{ burnDuration: 20 }} resolution={1} />
            </div>
            <dl className="fontMono grid grid-cols-2 gap-x-6 gap-y-2 text-[17px]">
              <dt className="text-mute">Wind</dt><dd className="text-ink">6 m/s → 80°</dd>
              <dt className="text-mute">Fuel moisture</dt><dd className="text-ink">10%</dd>
              <dt className="text-mute">Fuel map</dt><dd className="text-ink">fixed</dd>
              <dt className="text-mute">Terrain</dt><dd className="text-ink">fixed</dd>
            </dl>
          </div>
          <div className="glassPanel flex items-center justify-between rounded-2xl px-6 py-5">
            <div>
              <div className="fontMono text-[14px] uppercase tracking-[0.2em] text-mute">Runs required</div>
              <div className="text-[17px] text-mute">3 uncertain inputs × 3 values each</div>
            </div>
            <motion.div key={runCount} initial={reducedMotion ? false : { scale: 1.3, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="fontMono text-[64px] font-semibold text-ember">
              {runCount}
            </motion.div>
          </div>
        </div>

        <div className="relative" style={{ width: treeWidth, height: treeHeight }}>
          <svg width={treeWidth} height={treeHeight} className="absolute inset-0">
            {y1.map((y, i) => (
              <motion.path key={`a${i}`} d={branchPath(levelX[0], rootY, levelX[1], y)} stroke="#FF6B35" strokeOpacity={0.7} strokeWidth={2.5} fill="none" {...draw(step >= 1)} />
            ))}
            {y2.map((y, i) => (
              <motion.path key={`b${i}`} d={branchPath(levelX[1], y1[Math.floor(i / 3)], levelX[2] - 60, y)} stroke="#FF6B35" strokeOpacity={0.45} strokeWidth={2} fill="none" {...draw(step >= 1, 0.5)} />
            ))}
            {y3.map((y, i) => (
              <motion.path key={`c${i}`} d={branchPath(levelX[2] + 60, y2[Math.floor(i / 3)], levelX[3], y)} stroke="#FF6B35" strokeOpacity={0.3} strokeWidth={1.5} fill="none" {...draw(step >= 2, (i % 9) * 0.03)} />
            ))}
            <circle cx={levelX[0]} cy={rootY} r={16} fill="#FF6B35" />
            <circle cx={levelX[0]} cy={rootY} r={30} fill="none" stroke="#FF6B35" strokeOpacity={0.35} className="slowPulse" />
            {y1.map((y, i) => (
              <motion.g key={`n1${i}`} initial={false} animate={{ opacity: step >= 1 ? 1 : 0 }} transition={{ delay: step >= 1 && !reducedMotion ? 0.4 : 0 }}>
                <circle cx={levelX[1]} cy={y} r={10} fill="#FF6B35" />
                <text x={levelX[1]} y={y - 22} textAnchor="middle" className="fontMono" fontSize={15} fill="#94A3B8">wind → {windDirections[i]}°</text>
              </motion.g>
            ))}
            {y3.map((y, i) => (
              <motion.circle
                key={`n3${i}`}
                cx={levelX[3] + 12}
                cy={y}
                r={3 + Math.sqrt(leafFractions[i]) * 9}
                fill="#FF6B35"
                fillOpacity={0.35 + leafFractions[i] * 0.9}
                initial={false}
                animate={{ opacity: step >= 2 ? 1 : 0, scale: step >= 2 ? 1 : 0.3 }}
                transition={{ delay: step >= 2 && !reducedMotion ? 0.6 + (i % 9) * 0.03 : 0 }}
              />
            ))}
          </svg>
          {y2.map((y, i) => (
            <motion.div
              key={`t${i}`}
              className="absolute overflow-hidden rounded-md border border-white/15"
              style={{ left: levelX[2] - 60, top: y - 33, width: 120, height: 68 }}
              initial={false}
              animate={{ opacity: step >= 1 ? 1 : 0, scale: step >= 1 ? 1 : 0.85 }}
              transition={{ delay: step >= 1 && !reducedMotion ? 0.9 + i * 0.05 : 0 }}
            >
              <FireCanvas run={level2Runs[i]} time={horizon} width={120} height={68} bloom={false} options={{ showContours: false, burnDuration: 20 }} resolution={1} />
            </motion.div>
          ))}
          <Reveal show={step >= 2} delay={0.9} reducedMotion={reducedMotion} className="absolute -bottom-2 right-0 text-right">
            <div className="fontMono text-[15px] text-mute">leaf size = simulated burned area at a fixed horizon</div>
          </Reveal>
        </div>
      </div>
      <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between">
        <EvidenceBadge kind="illustration" detail="combinatorics, not measured workload" />
        <div className="fontDisplay text-[22px] text-ink/85">
          A simulated trajectory is <span className="text-ember">a model under assumptions</span>, not a record of what will happen.
        </div>
      </div>
    </SlideFrame>
  );
}
