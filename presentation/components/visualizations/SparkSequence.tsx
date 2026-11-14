"use client";
/**
 * Opening/closing cinematic: an ember drifts down, lands, terrain emerges, fire spreads,
 * and alternative futures flash as cyan fronts. Fully deterministic from scene time.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { FireCanvas, type FrontOverlay } from "./FireCanvas";
import { simulateFireSpread, sparkScenario } from "@/lib/fireModel";



const alternativeWinds = [10, 140, 210, 300];
const cellSize = 10; // 1920 / 192

export const sparkTimeline = { landAt: 2.6, fireStart: 2.9, futuresFrom: 5.0, settled: 11 };

function emberPosition(t: number, landX: number, landY: number) {
  // Gentle descending S-curve from upper left toward the landing point.
  const p = Math.min(1, Math.max(0, (t - 0.4) / (sparkTimeline.landAt - 0.4)));
  const eased = 1 - Math.pow(1 - p, 2.2);
  const startX = landX - 520;
  const startY = -40;
  const x = startX + (landX - startX) * eased + Math.sin(p * Math.PI * 2.4) * 46 * (1 - p);
  const y = startY + (landY - startY) * eased;
  return { x, y, landed: p >= 1 };
}

/** Scales a fixed-size scene to cover its container (like object-fit: cover), centered. */
function useCover(width: number, height: number) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [box, setBox] = useState({ w: width, h: height });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // offsetWidth/Height are layout sizes, unaffected by the stage's CSS scale transform.
    const measure = () => setBox({ w: el.offsetWidth || width, h: el.offsetHeight || height });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [width, height]);
  const scale = Math.max(box.w / width, box.h / height);
  return { ref, scale };
}

export function SparkSequence({ time, width = 1920, height = 1080, showFutures = true }: {
  time: number;
  width?: number;
  height?: number;
  showFutures?: boolean;
}) {
  const run = useMemo(() => simulateFireSpread(sparkScenario), []);
  const futures = useMemo(
    () => alternativeWinds.map((dir, k) => simulateFireSpread({ ...sparkScenario, windDirectionDeg: dir, windSpeed: 5 + k * 1.5 })),
    [],
  );

  const fireClock = Math.max(0, time - sparkTimeline.fireStart);
  const cap = run.maxArrival * 0.3;
  // Fast early growth that eases toward a cap so the frame never fills completely.
  const modelTime = cap * (1 - Math.exp(-fireClock / 4.2));
  const terrainReveal = Math.min(1, Math.max(0, (time - 1.2) / 2.6));

  const overlays: FrontOverlay[] = [];
  if (showFutures && time > sparkTimeline.futuresFrom) {
    const phase = time - sparkTimeline.futuresFrom;
    futures.forEach((future, k) => {
      const local = phase - k * 0.35;
      if (local <= 0) return;
      const pulse = 0.35 + 0.45 * Math.max(0, Math.sin(Math.min(Math.PI, local * 0.9)));
      const settledAlpha = phase > 4.5 ? 0.38 : pulse;
      overlays.push({ run: future, time: Math.min(cap, modelTime * 1.05 + 20), color: "#FFD27A", alpha: settledAlpha });
    });
  }

  const [ix, iy] = sparkScenario.ignitions[0];
  const landX = ix * cellSize + cellSize / 2;
  const landY = iy * cellSize + cellSize / 2;
  const ember = emberPosition(time, landX, landY);
  const flicker = 0.75 + 0.25 * Math.sin(time * 23) * Math.sin(time * 7.3);
  const emberOpacity = time < 0.4 ? time / 0.4 : ember.landed ? Math.max(0, 1 - (time - sparkTimeline.landAt) / 1.2) : 1;

  const cover = useCover(width, height);

  return (
    <div ref={cover.ref} className="absolute inset-0 overflow-hidden">
      <div
        className="absolute left-1/2 top-1/2"
        style={{ width, height, transform: `translate(-50%, -50%) scale(${cover.scale})`, transformOrigin: "center center" }}
      >
      <FireCanvas
        run={run}
        time={time < sparkTimeline.fireStart ? -1 : modelTime}
        width={width}
        height={height}
        options={{ terrainReveal, burnDuration: 46, showFuel: true, showContours: true }}
        sparks={time > sparkTimeline.fireStart}
        overlays={overlays}
        resolution={0.5}
        ariaLabel="Illustration: an ember lands and a fire spreads; cyan outlines show alternative futures"
      />
      {emberOpacity > 0 ? (
        <div
          className="pointer-events-none absolute rounded-full"
          style={{
            left: ember.x - 60,
            top: ember.y - 60,
            width: 120,
            height: 120,
            opacity: emberOpacity,
            background: `radial-gradient(circle, rgba(255,241,214,${flicker}) 0%, rgba(255,181,71,${0.85 * flicker}) 8%, rgba(255,107,53,0.45) 22%, rgba(229,57,53,0.12) 45%, transparent 70%)`,
            filter: "blur(0.5px)",
          }}
        />
      ) : null}
      </div>
    </div>
  );
}
