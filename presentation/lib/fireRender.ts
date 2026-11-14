/** Pixel painters for fire fields, masks and scalar layers (one pixel per grid cell). */
import type { FireRun, TerrainField } from "./fireModel";

export interface FireFrameOptions {
  time: number;
  showFire: boolean;
  showTerrain: boolean;
  showContours: boolean;
  showFuel: boolean;
  isochroneStep?: number; // draw progression lines every N model-time units
  burnDuration: number;
  terrainReveal?: number; // 0..1 fade-in of terrain
}

const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);

/** Terrain base color: volcanic dark relief with faint topographic contours. */
function terrainColor(t: TerrainField, i: number, opts: FireFrameOptions): [number, number, number] {
  if (t.water[i]) return [8, 20, 34];
  const shade = t.hillshade[i];
  const e = t.elevation[i];
  let r = 14 + shade * 26 + e * 10;
  let g = 18 + shade * 28 + e * 8;
  let b = 24 + shade * 30 + e * 6;
  if (opts.showFuel) {
    const f = t.fuel[i];
    r += f * 4;
    g += f * 13;
    b += f * 6;
  }
  if (opts.showContours) {
    const band = (e * 22) % 1;
    if (band < 0.08) {
      r += 18;
      g += 26;
      b += 34;
    }
  }
  return [r, g, b];
}

/** Paints a full fire frame into ImageData sized width x height. */
export function paintFireFrame(image: ImageData, run: FireRun, opts: FireFrameOptions): void {
  const { terrain, arrival } = run;
  const data = image.data;
  const reveal = opts.terrainReveal ?? 1;
  const step = opts.isochroneStep ?? 0;
  const w = terrain.width;

  for (let i = 0; i < arrival.length; i++) {
    let [r, g, b] = opts.showTerrain ? terrainColor(terrain, i, opts) : [8, 11, 16];
    r *= reveal;
    g *= reveal;
    b *= reveal;
    const a = arrival[i];
    if (opts.showFire && a <= opts.time) {
      const age = opts.time - a;
      if (age < opts.burnDuration) {
        // Active front: white-yellow core cooling to orange-red.
        const k = age / opts.burnDuration;
        r = 255;
        g = 235 - 150 * k;
        b = 140 - 120 * k;
      } else {
        // Burned scar: charcoal with fading residual heat.
        const cool = clamp01((age - opts.burnDuration) / (opts.burnDuration * 4));
        r = 70 - 44 * cool;
        g = 26 - 10 * cool;
        b = 18 - 2 * cool;
      }
    }
    if (step > 0 && opts.showFire && a <= opts.time && a !== Infinity) {
      // Isochrone: cell is on a progression line if a neighbor crosses the next band.
      const band = Math.floor(a / step);
      const right = i % w < w - 1 ? arrival[i + 1] : a;
      const down = i + w < arrival.length ? arrival[i + w] : a;
      if (Math.floor(right / step) !== band || Math.floor(down / step) !== band) {
        r = 255;
        g = 190;
        b = 120;
      }
    }
    const o = i * 4;
    data[o] = r;
    data[o + 1] = g;
    data[o + 2] = b;
    data[o + 3] = 255;
  }
}

export type ColorRamp = (v: number) => [number, number, number];

/** Sequential ramps keyed to the semantic palette. */
export const ramps: Record<string, ColorRamp> = {
  ember: (v) => [20 + 235 * v, 14 + 110 * v * v, 16 + 40 * v * v * v],
  cyan: (v) => [10 + 62 * v, 18 + 198 * v, 28 + 227 * v],
  slate: (v) => [18 + 130 * v, 22 + 140 * v, 30 + 154 * v],
  verified: (v) => [12 + 41 * v, 20 + 194 * v, 24 + 136 * v],
  /** Diverging: negative (under-prediction) cyan, positive (over-prediction) ember. */
  diverging: (v) => {
    const c = v * 2 - 1;
    if (c < 0) return [20 - 10 * c, 24 - 190 * c, 32 - 223 * c];
    return [20 + 235 * c, 24 + 83 * c, 32 + 21 * c];
  },
};

/** Paints a scalar field (0..1) through a ramp. */
export function paintScalarField(image: ImageData, values: ArrayLike<number>, ramp: ColorRamp, mask?: Uint8Array): void {
  const data = image.data;
  for (let i = 0; i < values.length; i++) {
    const [r, g, b] = mask && mask[i] ? [8, 20, 34] : ramp(clamp01(values[i]));
    const o = i * 4;
    data[o] = r;
    data[o + 1] = g;
    data[o + 2] = b;
    data[o + 3] = 255;
  }
}

export interface MaskComparisonColors {
  truePositive: [number, number, number];
  falsePositive: [number, number, number];
  falseNegative: [number, number, number];
  background: [number, number, number];
}

export const comparisonColors: MaskComparisonColors = {
  truePositive: [200, 210, 222],
  falsePositive: [255, 107, 53], // predicted burned, reference not: over-prediction
  falseNegative: [72, 216, 255], // reference burned, predicted not: under-prediction
  background: [14, 18, 26],
};

/** Paints a reference/prediction difference map using the comparison legend. */
export function paintDifferenceMap(image: ImageData, reference: Uint8Array, prediction: Uint8Array): void {
  const data = image.data;
  for (let i = 0; i < reference.length; i++) {
    const ref = reference[i];
    const pred = prediction[i];
    const c = ref && pred ? comparisonColors.truePositive
      : pred ? comparisonColors.falsePositive
      : ref ? comparisonColors.falseNegative
      : comparisonColors.background;
    const o = i * 4;
    data[o] = c[0];
    data[o + 1] = c[1];
    data[o + 2] = c[2];
    data[o + 3] = 255;
  }
}

/** Paints a binary mask in a single color over a dark ground. */
export function paintBinaryMask(image: ImageData, mask: Uint8Array, color: [number, number, number]): void {
  const data = image.data;
  for (let i = 0; i < mask.length; i++) {
    const o = i * 4;
    const on = mask[i];
    data[o] = on ? color[0] : 14;
    data[o + 1] = on ? color[1] : 18;
    data[o + 2] = on ? color[2] : 26;
    data[o + 3] = 255;
  }
}
