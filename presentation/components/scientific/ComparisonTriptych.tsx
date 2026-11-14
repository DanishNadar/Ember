"use client";
/**
 * Synchronized reference / prediction / difference panels for one held-out example.
 * All three share resolution, alignment and coordinate system. Per-example metrics are
 * recomputed from the masks when masks are provided.
 */
import { useMemo } from "react";
import type { FidelityExample } from "@/data/schemas/presentationSchema";
import { PixelCanvas } from "./PixelCanvas";
import { comparisonColors, paintBinaryMask, paintDifferenceMap } from "@/lib/fireRender";
import { computeMaskAgreement, decodeRowMask } from "@/lib/maskMetrics";

const rgb = (c: [number, number, number]) => `rgb(${c[0]},${c[1]},${c[2]})`;

export function useDecodedExample(example: FidelityExample | null) {
  return useMemo(() => {
    if (!example?.referenceMask || !example?.predictionMask) return null;
    const reference = decodeRowMask(example.referenceMask);
    const prediction = decodeRowMask(example.predictionMask);
    if (reference.width !== prediction.width || reference.height !== prediction.height) return null;
    return { reference, prediction, agreement: computeMaskAgreement(reference.mask, prediction.mask) };
  }, [example]);
}

function PanelLabel({ title, color }: { title: string; color: string }) {
  return (
    <div className="fontMono mb-2 flex items-center gap-2 text-[16px] uppercase tracking-[0.16em]" style={{ color }}>
      <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} /> {title}
    </div>
  );
}

export function ComparisonTriptych({ example, panelSize, overlayOpacity = 1, overlayMode = false }: {
  example: FidelityExample;
  panelSize: number;
  overlayOpacity?: number;
  overlayMode?: boolean;
}) {
  const decoded = useDecodedExample(example);

  if (!decoded) {
    // Image-based examples (pre-rendered PNGs from the experiment).
    const images = [
      { title: "Simulator reference", src: example.referenceImage, color: "#FF6B35" },
      { title: "Surrogate prediction", src: example.predictionImage, color: "#48D8FF" },
      { title: "Difference", src: example.errorImage, color: "#94A3B8" },
    ];
    return (
      <div className="flex gap-6">
        {images.map((img) => (
          <div key={img.title}>
            <PanelLabel title={img.title} color={img.color} />
            {img.src ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={img.src} alt={img.title} width={panelSize} height={panelSize} className="rounded-xl border border-white/10 object-contain" style={{ width: panelSize, height: panelSize, imageRendering: "pixelated" }} />
            ) : (
              <div className="flex items-center justify-center rounded-xl border border-dashed border-white/15 text-mute" style={{ width: panelSize, height: panelSize }}>not provided</div>
            )}
          </div>
        ))}
      </div>
    );
  }

  const { reference, prediction } = decoded;
  return (
    <div className="flex gap-6">
      <div>
        <PanelLabel title="Simulator reference" color="#FF6B35" />
        <div className="overflow-hidden rounded-xl border border-white/10">
          <PixelCanvas gridWidth={reference.width} gridHeight={reference.height} displayWidth={panelSize} displayHeight={panelSize} paintKey={example.id} paint={(img) => paintBinaryMask(img, reference.mask, [255, 107, 53])} ariaLabel="Simulator reference mask" />
        </div>
      </div>
      <div>
        <PanelLabel title="Surrogate prediction" color="#48D8FF" />
        <div className="relative overflow-hidden rounded-xl border border-white/10">
          <PixelCanvas gridWidth={prediction.width} gridHeight={prediction.height} displayWidth={panelSize} displayHeight={panelSize} paintKey={example.id} paint={(img) => paintBinaryMask(img, prediction.mask, [72, 216, 255])} ariaLabel="Surrogate prediction mask" />
          {overlayMode ? (
            <div className="absolute inset-0" style={{ opacity: overlayOpacity, mixBlendMode: "screen" }}>
              <PixelCanvas gridWidth={reference.width} gridHeight={reference.height} displayWidth={panelSize} displayHeight={panelSize} paintKey={`${example.id}-ov`} paint={(img) => paintBinaryMask(img, reference.mask, [255, 107, 53])} ariaLabel="Reference overlay" />
            </div>
          ) : null}
        </div>
      </div>
      <div>
        <PanelLabel title="Difference" color="#94A3B8" />
        <div className="overflow-hidden rounded-xl border border-white/10">
          <PixelCanvas gridWidth={reference.width} gridHeight={reference.height} displayWidth={panelSize} displayHeight={panelSize} paintKey={example.id} paint={(img) => paintDifferenceMap(img, reference.mask, prediction.mask)} ariaLabel="Difference map" />
        </div>
      </div>
    </div>
  );
}

export function DifferenceLegend() {
  const items: Array<[string, [number, number, number]]> = [
    ["both burned (agree)", comparisonColors.truePositive],
    ["over-predicted (false positive)", comparisonColors.falsePositive],
    ["missed (false negative)", comparisonColors.falseNegative],
  ];
  return (
    <div className="fontMono flex gap-6 text-[15px] text-mute">
      {items.map(([label, color]) => (
        <span key={label} className="flex items-center gap-2"><span className="inline-block h-3 w-3 rounded-sm" style={{ background: rgb(color) }} /> {label}</span>
      ))}
    </div>
  );
}
