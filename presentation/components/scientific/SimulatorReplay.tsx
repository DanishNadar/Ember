"use client";
/**
 * Simulator replay viewer with play/pause, time scrubber and layer toggles.
 * Uses the recorded simulator replay when ingested (simulator-derived); otherwise falls
 * back to a clearly labeled illustrative stand-in driven by the deck's toy model.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { Pause, Play, RotateCcw } from "lucide-react";
import type { SimulatorInfo } from "@/data/schemas/presentationSchema";
import { FireCanvas } from "@/components/visualizations/FireCanvas";
import { PixelCanvas } from "./PixelCanvas";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { baseScenario, simulateFireSpread } from "@/lib/fireModel";
import { decodeRowMask } from "@/lib/maskMetrics";
import { ramps } from "@/lib/fireRender";
import { useAnimationClock } from "@/hooks/useAnimationClock";

function Toggle({ label, on, onClick, color = "#FF6B35" }: { label: string; on: boolean; onClick: () => void; color?: string }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={on}
      className="fontMono flex items-center gap-2 rounded-lg border px-3 py-2 text-[15px] transition"
      style={{ borderColor: on ? `${color}88` : "rgba(148,163,184,0.2)", color: on ? color : "#94A3B8", background: on ? `${color}14` : "transparent" }}
    >
      <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: on ? color : "transparent", border: `1px solid ${color}` }} />
      {label}
    </button>
  );
}

export function SimulatorReplay({ simulator, isFixture, width, height, active, reducedMotion }: {
  simulator: SimulatorInfo | null;
  isFixture: boolean;
  width: number;
  height: number;
  active: boolean;
  reducedMotion: boolean;
}) {
  const replay = simulator?.replay ?? null;
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0.4); // 0..1 along the replay
  const [showFire, setShowFire] = useState(true);
  const [showLayers, setShowLayers] = useState(true);
  const [showProgression, setShowProgression] = useState(false);
  const [layerName, setLayerName] = useState<string>(replay?.layers ? Object.keys(replay.layers)[0] : "fuel");
  const [resetKey, setResetKey] = useState(0);
  const clock = useAnimationClock(active && playing, resetKey, 30);
  const playStartRef = useRef(0);

  // Advance playback from where play was pressed; a full sweep takes ~9 s. Stop at the end.
  useEffect(() => {
    if (!playing) return;
    const next = Math.min(1, playStartRef.current + clock / 9);
    setPosition(next);
    if (next >= 1) setPlaying(false);
  }, [clock, playing]);

  useEffect(() => {
    if (!active) setPlaying(false);
  }, [active]);

  const illustrativeRun = useMemo(() => simulateFireSpread(baseScenario), []);
  const decodedFrames = useMemo(() => (replay ? replay.frames.map(decodeRowMask) : []), [replay]);

  const controls = (
    <div className="flex items-center gap-4">
      <button
        onClick={() => {
          if (!playing) {
            playStartRef.current = position >= 1 ? 0 : position;
            if (position >= 1) setPosition(0);
            setResetKey((k) => k + 1);
          }
          setPlaying((p) => !p);
        }}
        className="flex h-11 w-11 items-center justify-center rounded-full bg-ember text-black hover:brightness-110"
        aria-label={playing ? "Pause replay" : "Play replay"}
      >
        {playing ? <Pause size={20} /> : <Play size={20} className="ml-0.5" />}
      </button>
      <button onClick={() => { setPlaying(false); setPosition(0); setResetKey((k) => k + 1); }} className="rounded-full p-2 text-mute hover:text-ink" aria-label="Restart replay">
        <RotateCcw size={18} />
      </button>
      <input
        type="range"
        min={0}
        max={1000}
        value={Math.round(position * 1000)}
        onChange={(e) => {
          setPlaying(false);
          setPosition(Number(e.target.value) / 1000);
          setResetKey((k) => k + 1);
        }}
        className="emberRange flex-1"
        aria-label="Simulation time"
      />
    </div>
  );

  if (replay && decodedFrames.length > 0) {
    const frameIndex = Math.min(decodedFrames.length - 1, Math.round(position * (decodedFrames.length - 1)));
    const frame = decodedFrames[frameIndex];
    const layer = replay.layers?.[layerName] ?? null;
    const flatLayer = layer ? layer.flat() : null;
    return (
      <div className="flex flex-col gap-4">
        <div className="relative overflow-hidden rounded-2xl border border-white/10" style={{ width, height }}>
          <PixelCanvas
            gridWidth={frame.width}
            gridHeight={frame.height}
            displayWidth={width}
            displayHeight={height}
            paintKey={`${frameIndex}-${showFire}-${showLayers}-${showProgression}-${layerName}`}
            ariaLabel={`Recorded simulator frame ${frameIndex + 1} of ${decodedFrames.length}`}
            paint={(image) => {
              const d = image.data;
              for (let i = 0; i < frame.mask.length; i++) {
                let [r, g, b] = showLayers && flatLayer ? ramps.slate(flatLayer[i] ?? 0) : [14, 18, 26];
                if (showProgression) {
                  // Earliest frame that burned this cell → isochrone shading.
                  for (let f = 0; f <= frameIndex; f++) {
                    if (decodedFrames[f].mask[i]) {
                      const k = f / Math.max(1, decodedFrames.length - 1);
                      [r, g, b] = ramps.ember(0.35 + 0.65 * (1 - k));
                      break;
                    }
                  }
                } else if (showFire && frame.mask[i]) {
                  [r, g, b] = [255, 107, 53];
                }
                d[i * 4] = r;
                d[i * 4 + 1] = g;
                d[i * 4 + 2] = b;
                d[i * 4 + 3] = 255;
              }
            }}
          />
          <div className="absolute left-4 top-4">
            <EvidenceBadge kind={isFixture ? "illustration" : "simulatorDerived"} isFixture={isFixture} detail={`${simulator?.name} · scenario ${replay.scenarioId}`} />
          </div>
          <div className="fontMono absolute right-4 top-4 rounded-lg bg-black/60 px-3 py-1.5 text-[16px] text-ink">
            t = {replay.frameTimes[frameIndex]} {replay.timeUnit} · frame {frameIndex + 1}/{decodedFrames.length}
          </div>
        </div>
        {controls}
        <div className="flex flex-wrap gap-2">
          <Toggle label="Fire extent" on={showFire} onClick={() => setShowFire((v) => !v)} />
          <Toggle label="Environment layer" on={showLayers} onClick={() => setShowLayers((v) => !v)} color="#94A3B8" />
          <Toggle label="Progression" on={showProgression} onClick={() => setShowProgression((v) => !v)} color="#FFB547" />
          {replay.layers ? (
            <select value={layerName} onChange={(e) => setLayerName(e.target.value)} className="fontMono rounded-lg border border-white/15 bg-basalt px-3 text-[15px] text-ink">
              {Object.keys(replay.layers).map((name) => <option key={name}>{name}</option>)}
            </select>
          ) : null}
        </div>
      </div>
    );
  }

  const modelTime = position * illustrativeRun.maxArrival * 0.6;
  return (
    <div className="flex flex-col gap-4">
      <div className="relative overflow-hidden rounded-2xl border border-white/10" style={{ width, height }}>
        <FireCanvas
          run={illustrativeRun}
          time={modelTime}
          width={width}
          height={height}
          windArrows={showLayers}
          sparks={playing}
          options={{
            showFire,
            showFuel: showLayers,
            showContours: showLayers,
            isochroneStep: showProgression ? illustrativeRun.maxArrival / 18 : 0,
            burnDuration: 36,
          }}
          ariaLabel="Illustrative stand-in replay (toy model, not simulator output)"
        />
        <div className="absolute left-4 top-4 flex flex-col items-start gap-2">
          <EvidenceBadge kind="illustration" detail="stand-in: no recorded simulator replay ingested" />
        </div>
        <div className="fontMono absolute right-4 top-4 rounded-lg bg-black/60 px-3 py-1.5 text-[16px] text-ink">
          t = {Math.round(position * 100)}% of horizon
        </div>
      </div>
      {controls}
      <div className="flex flex-wrap gap-2">
        <Toggle label="Fire extent" on={showFire} onClick={() => setShowFire((v) => !v)} />
        <Toggle label="Environment layers" on={showLayers} onClick={() => setShowLayers((v) => !v)} color="#48D8FF" />
        <Toggle label="Progression lines" on={showProgression} onClick={() => setShowProgression((v) => !v)} color="#FFB547" />
      </div>
    </div>
  );
}
