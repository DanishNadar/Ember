"use client";
/** One input/target channel rendered as a labeled tile. */
import { PixelCanvas } from "./PixelCanvas";
import { paintBinaryMask, paintScalarField, ramps } from "@/lib/fireRender";

export type ChannelSpec =
  | { kind: "mask"; name: string; mask: Uint8Array; color?: [number, number, number] }
  | { kind: "scalar"; name: string; values: ArrayLike<number>; ramp?: keyof typeof ramps; arrowDeg?: number };

export function ChannelTile({ spec, gridWidth, gridHeight, width, height, caption }: {
  spec: ChannelSpec;
  gridWidth: number;
  gridHeight: number;
  width: number;
  height: number;
  caption?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="relative overflow-hidden rounded-lg border border-white/15" style={{ width, height }}>
        <PixelCanvas
          gridWidth={gridWidth}
          gridHeight={gridHeight}
          displayWidth={width}
          displayHeight={height}
          smooth={spec.kind === "scalar"}
          paintKey={spec}
          ariaLabel={`${spec.name} channel`}
          paint={(image) => {
            if (spec.kind === "mask") paintBinaryMask(image, spec.mask, spec.color ?? [255, 107, 53]);
            else paintScalarField(image, spec.values, ramps[spec.ramp ?? "slate"]);
          }}
        />
        {spec.kind === "scalar" && spec.arrowDeg !== undefined ? (
          <svg className="absolute inset-0" width={width} height={height}>
            <g transform={`translate(${width / 2} ${height / 2}) rotate(${spec.arrowDeg})`}>
              <line x1={0} y1={18} x2={0} y2={-18} stroke="#F3F6FA" strokeWidth={3} />
              <path d="M-8,-10 L0,-22 L8,-10" fill="none" stroke="#F3F6FA" strokeWidth={3} />
            </g>
          </svg>
        ) : null}
      </div>
      <div className="fontMono text-[15px] text-ink/90">{spec.name}</div>
      {caption ? <div className="fontMono -mt-1 text-[12px] text-mute">{caption}</div> : null}
    </div>
  );
}
