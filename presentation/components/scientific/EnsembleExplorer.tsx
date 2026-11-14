"use client";
/**
 * One footprint → many footprints → agreement map. Uses a recorded ensemble when one is
 * ingested; otherwise an illustrative ensemble from the deck's toy model (labeled).
 * Agreement = fraction of members burning a cell. It is NOT a calibrated probability.
 */
import { useEffect, useMemo, useState } from "react";
import type { EnsembleResults } from "@/data/schemas/presentationSchema";
import { PixelCanvas } from "./PixelCanvas";
import { EvidenceBadge } from "@/components/presentation/EvidenceBadge";
import { baseScenario, buildIllustrativeEnsemble, burnedMaskAt, simulateFireSpread } from "@/lib/fireModel";
import { decodeRowMask } from "@/lib/maskMetrics";
import { ramps } from "@/lib/fireRender";
import { formatPercent } from "@/lib/format";

export type EnsembleView = "single" | "many" | "agreement";

const maxMembers = 24;

export function EnsembleExplorer({ ensemble, isFixture, view, onViewChange, width, height, showSummary }: {
  ensemble: EnsembleResults | null;
  isFixture: boolean;
  view: EnsembleView;
  onViewChange: (v: EnsembleView) => void;
  width: number;
  height: number;
  showSummary: boolean;
}) {
  const source = useMemo(() => {
    if (ensemble && ensemble.members.length > 0) {
      const decoded = ensemble.members.map((m) => decodeRowMask(m.mask));
      return { kind: "recorded" as const, masks: decoded.map((d) => d.mask), labels: ensemble.members.map((m) => m.label), gridWidth: decoded[0].width, gridHeight: decoded[0].height, shade: null as Float32Array | null };
    }
    const runs = buildIllustrativeEnsemble(baseScenario, maxMembers, 7);
    const horizon = simulateFireSpread(baseScenario).maxArrival * 0.17;
    return {
      kind: "illustrative" as const,
      masks: runs.map((r) => burnedMaskAt(r, horizon)),
      labels: runs.map((r) => `wind ${r.params.windSpeed} m/s → ${r.params.windDirectionDeg}°, moisture ${Math.round(r.params.fuelMoisture * 100)}%`),
      gridWidth: baseScenario.width,
      gridHeight: baseScenario.height,
      shade: runs[0].terrain.hillshade,
    };
  }, [ensemble]);

  const available = source.masks.length;
  const [memberCount, setMemberCount] = useState(Math.min(12, available));
  const [selectedMember, setSelectedMember] = useState(0);
  useEffect(() => setSelectedMember((s) => Math.min(s, memberCount - 1)), [memberCount]);

  const effectiveCount = view === "single" ? 1 : memberCount;
  const agreement = useMemo(() => {
    const size = source.gridWidth * source.gridHeight;
    const counts = new Float32Array(size);
    for (let m = 0; m < memberCount; m++) {
      const mask = source.masks[m];
      for (let i = 0; i < size; i++) counts[i] += mask[i];
    }
    for (let i = 0; i < size; i++) counts[i] /= memberCount;
    return counts;
  }, [source, memberCount]);

  const summary = useMemo(() => {
    let any = 0;
    let high = 0;
    let disputed = 0;
    for (const a of agreement) {
      if (a > 0) any++;
      if (a >= 0.9) high++;
      else if (a > 0.1) disputed++;
    }
    return { any, high, disputed };
  }, [agreement]);

  const paint = (image: ImageData) => {
    const d = image.data;
    const size = source.gridWidth * source.gridHeight;
    const selectedMask = source.masks[selectedMember];
    for (let i = 0; i < size; i++) {
      const s = source.shade ? source.shade[i] : 0.4;
      let r = 22 + s * 34;
      let g = 12 + s * 18;
      let b = 10 + s * 12;
      if (view === "single") {
        if (selectedMask[i]) [r, g, b] = [255, 107, 53];
      } else if (view === "many") {
        // Outline every member's footprint; overlapping edges accumulate brightness.
        let edges = 0;
        const x = i % source.gridWidth;
        for (let m = 0; m < memberCount; m++) {
          const mask = source.masks[m];
          if (!mask[i]) continue;
          if (x === 0 || x === source.gridWidth - 1 || !mask[i - 1] || !mask[i + 1] || !mask[i - source.gridWidth] || !mask[i + source.gridWidth]) edges++;
        }
        if (edges > 0) {
          const k = Math.min(1, 0.35 + edges / 6);
          [r, g, b] = [255 * k, 107 * k + 40 * k, 53 * k];
        }
        if (selectedMask[i] && (!selectedMask[i - 1] || !selectedMask[i + 1])) [r, g, b] = [72, 216, 255];
      } else if (agreement[i] > 0) {
        [r, g, b] = ramps.ember(0.25 + 0.75 * agreement[i]);
      }
      d[i * 4] = r;
      d[i * 4 + 1] = g;
      d[i * 4 + 2] = b;
      d[i * 4 + 3] = 255;
    }
  };

  return (
    <div className="flex gap-8">
      <div className="relative overflow-hidden rounded-2xl border border-white/10" style={{ width, height }}>
        <PixelCanvas gridWidth={source.gridWidth} gridHeight={source.gridHeight} displayWidth={width} displayHeight={height} smooth paintKey={`${view}-${memberCount}-${selectedMember}-${source.kind}`} paint={paint} ariaLabel={`Ensemble ${view} view with ${effectiveCount} members`} />
        <div className="absolute left-4 top-4">
          {source.kind === "recorded" ? (
            <EvidenceBadge kind={isFixture ? "illustration" : "verified"} isFixture={isFixture} detail={ensemble?.source.path} />
          ) : (
            <EvidenceBadge kind="proposed" detail="illustrative ensemble · toy model" />
          )}
        </div>
        {view === "agreement" ? (
          <div className="glassPanel absolute bottom-4 left-4 rounded-xl px-4 py-3">
            <div className="fontMono mb-1 text-[13px] text-mute">fraction of members burning the cell</div>
            <div className="h-3 w-[260px] rounded-sm" style={{ background: "linear-gradient(90deg, rgb(89,45,22), rgb(255,124,56))" }} />
            <div className="fontMono mt-1 flex justify-between text-[12px] text-mute"><span>1 / {memberCount}</span><span>all {memberCount}</span></div>
          </div>
        ) : null}
      </div>

      <div className="flex w-[400px] flex-col gap-5">
        <div className="flex rounded-xl border border-white/10 bg-basalt p-1">
          {([["single", "One footprint"], ["many", "Many footprints"], ["agreement", "Agreement heatmap"]] as const).map(([key, label]) => (
            <button key={key} onClick={() => onViewChange(key)} aria-pressed={view === key} className={`fontMono flex-1 rounded-lg px-2 py-2 text-[14px] ${view === key ? "bg-ember/15 text-ember" : "text-mute hover:text-ink"}`}>
              {label}
            </button>
          ))}
        </div>
        <label className="block">
          <div className="fontMono mb-2 flex justify-between text-[15px] text-mute"><span>Ensemble size</span><span className="text-ink">{memberCount}</span></div>
          <input type="range" min={1} max={available} value={memberCount} onChange={(e) => setMemberCount(Number(e.target.value))} className="emberRange w-full" aria-label="Displayed ensemble size" />
        </label>
        <div>
          <div className="fontMono mb-2 text-[15px] text-mute">Select member</div>
          <div className="flex flex-wrap gap-1.5">
            {Array.from({ length: memberCount }, (_, k) => (
              <button key={k} onClick={() => setSelectedMember(k)} className={`fontMono h-8 w-8 rounded-md text-[13px] ${k === selectedMember ? "bg-[#48D8FF] text-black" : "bg-white/5 text-mute hover:text-ink"}`} aria-label={`Member ${k + 1}`}>
                {k + 1}
              </button>
            ))}
          </div>
          <div className="fontMono mt-2 text-[13px] text-mute">#{selectedMember + 1}: {source.labels[selectedMember]}</div>
        </div>
        {showSummary ? (
          <div className="glassPanel rounded-2xl p-5">
            <div className="fontMono mb-3 text-[13px] uppercase tracking-[0.2em] text-mute">Uncertainty summary · {memberCount} members</div>
            <div className="grid grid-cols-2 gap-y-2 text-[17px]">
              <span className="text-mute">Burned in ≥ 90% of members</span><span className="fontMono text-right text-ink">{formatPercent(summary.high / Math.max(1, summary.any))}</span>
              <span className="text-mute">Disputed (10–90%)</span><span className="fontMono text-right text-ink">{formatPercent(summary.disputed / Math.max(1, summary.any))}</span>
              <span className="text-mute">Cells burned by any member</span><span className="fontMono text-right text-ink">{summary.any.toLocaleString()}</span>
            </div>
            <div className="mt-3 text-[13px] leading-snug text-mute">Raw member agreement, not a calibrated probability. Calibration would need validation against observed fires.</div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
