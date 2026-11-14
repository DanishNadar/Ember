/**
 * ILLUSTRATIVE fire-spread model used only for presentation visuals.
 *
 * This is NOT the project's scientific simulator and NOT ForeFire. It is a small,
 * deterministic minimum-travel-time model on a grid (in the spirit of Dijkstra-based
 * arrival-time methods) so the deck can animate plausible-looking fronts offline.
 * Every visual driven by this file is badged "Architectural illustration".
 */
import { createSeededRandom, fractalNoise } from "./seededRandom";

export interface TerrainField {
  width: number;
  height: number;
  elevation: Float32Array; // 0..1
  fuel: Float32Array; // 0..1, 0 = non-burnable
  water: Uint8Array; // 1 = water body
  hillshade: Float32Array; // 0..1 lighting term
  slope: Float32Array; // gradient magnitude
  roughness: Float32Array; // per-cell spread-rate jitter
}

export interface FireScenarioParams {
  width: number;
  height: number;
  terrainSeed: number;
  /** Direction the wind blows TOWARD, compass degrees (0 = up/north, 90 = right/east). */
  windDirectionDeg: number;
  /** Wind speed in illustrative m/s units (0–20). */
  windSpeed: number;
  /** Dead fuel moisture as a fraction (0–1). */
  fuelMoisture: number;
  /** Ignition cells in grid coordinates. */
  ignitions: Array<[number, number]>;
}

export interface FireRun {
  params: FireScenarioParams;
  terrain: TerrainField;
  arrival: Float32Array; // model time of ignition per cell, Infinity if never
  maxArrival: number; // largest finite arrival time
}

const terrainCache = new Map<string, TerrainField>();
const runCache = new Map<string, FireRun>();

export const defaultGrid = { width: 192, height: 108 } as const;

export function generateTerrain(seed: number, width: number, height: number): TerrainField {
  const key = `${seed}:${width}x${height}`;
  const cached = terrainCache.get(key);
  if (cached) return cached;

  const size = width * height;
  const elevation = new Float32Array(size);
  const fuel = new Float32Array(size);
  const water = new Uint8Array(size);
  const hillshade = new Float32Array(size);
  const slope = new Float32Array(size);
  const roughness = new Float32Array(size);
  const scale = 1 / 46;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      // Ridge-biased terrain: a broad ridge running diagonally plus fractal detail.
      const ridge = 0.35 * Math.exp(-Math.pow((x / width - 0.15 - 0.6 * (y / height)) * 3.2, 2));
      elevation[i] = Math.min(1, 0.65 * fractalNoise(x * scale, y * scale, seed) + ridge);
    }
  }

  const random = createSeededRandom(seed * 7 + 3);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      const e = elevation[i];
      const left = elevation[y * width + Math.max(0, x - 1)];
      const right = elevation[y * width + Math.min(width - 1, x + 1)];
      const up = elevation[Math.max(0, y - 1) * width + x];
      const down = elevation[Math.min(height - 1, y + 1) * width + x];
      const dx = (right - left) * 6;
      const dy = (down - up) * 6;
      slope[i] = Math.hypot(dx, dy);
      // Light from the upper-left for a relief-map look.
      const shade = (-dx * 0.7 - dy * 0.7 + 1) / Math.sqrt(dx * dx + dy * dy + 1);
      hillshade[i] = Math.max(0, Math.min(1, 0.5 + 0.5 * shade));

      const isWater = e < 0.285;
      water[i] = isWater ? 1 : 0;
      const vegetation = fractalNoise(x / 18 + 50, y / 18 + 50, seed + 999, 3);
      fuel[i] = isWater ? 0 : Math.max(0.08, Math.min(1, 0.25 + vegetation * 0.95));
      roughness[i] = 0.7 + random() * 0.6;
    }
  }

  const field: TerrainField = { width, height, elevation, fuel, water, hillshade, slope, roughness };
  terrainCache.set(key, field);
  return field;
}

/** Minimal binary min-heap keyed by float priority. */
class MinHeap {
  private keys: number[] = [];
  private values: number[] = [];
  get size() {
    return this.keys.length;
  }
  push(key: number, value: number) {
    this.keys.push(key);
    this.values.push(value);
    let i = this.keys.length - 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (this.keys[parent] <= this.keys[i]) break;
      this.swap(i, parent);
      i = parent;
    }
  }
  pop(): [number, number] {
    const topKey = this.keys[0];
    const topValue = this.values[0];
    const lastKey = this.keys.pop()!;
    const lastValue = this.values.pop()!;
    if (this.keys.length > 0) {
      this.keys[0] = lastKey;
      this.values[0] = lastValue;
      let i = 0;
      const n = this.keys.length;
      for (;;) {
        const l = 2 * i + 1;
        const r = l + 1;
        let smallest = i;
        if (l < n && this.keys[l] < this.keys[smallest]) smallest = l;
        if (r < n && this.keys[r] < this.keys[smallest]) smallest = r;
        if (smallest === i) break;
        this.swap(i, smallest);
        i = smallest;
      }
    }
    return [topKey, topValue];
  }
  private swap(a: number, b: number) {
    [this.keys[a], this.keys[b]] = [this.keys[b], this.keys[a]];
    [this.values[a], this.values[b]] = [this.values[b], this.values[a]];
  }
}

const neighborOffsets: Array<[number, number, number]> = [
  [1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1],
  [1, 1, Math.SQRT2], [1, -1, Math.SQRT2], [-1, 1, Math.SQRT2], [-1, -1, Math.SQRT2],
];

function scenarioKey(p: FireScenarioParams): string {
  return [p.width, p.height, p.terrainSeed, p.windDirectionDeg.toFixed(1), p.windSpeed.toFixed(2),
    p.fuelMoisture.toFixed(3), p.ignitions.map((c) => c.join(",")).join(";")].join("|");
}

/** Computes per-cell arrival time with a deterministic minimum-travel-time sweep. */
export function simulateFireSpread(params: FireScenarioParams): FireRun {
  const key = scenarioKey(params);
  const cached = runCache.get(key);
  if (cached) return cached;

  const { width, height } = params;
  const terrain = generateTerrain(params.terrainSeed, width, height);
  const size = width * height;
  const arrival = new Float32Array(size).fill(Infinity);
  const heap = new MinHeap();

  const windRad = (params.windDirectionDeg * Math.PI) / 180;
  const windX = Math.sin(windRad);
  const windY = -Math.cos(windRad);
  const windStrength = Math.min(20, Math.max(0, params.windSpeed)) / 7;
  const moistureFactor = Math.exp(-3.2 * Math.min(1, Math.max(0, params.fuelMoisture)));

  for (const [x, y] of params.ignitions) {
    const i = Math.round(y) * width + Math.round(x);
    if (i >= 0 && i < size && terrain.fuel[i] > 0) {
      arrival[i] = 0;
      heap.push(0, i);
    }
  }

  while (heap.size > 0) {
    const [time, index] = heap.pop();
    if (time > arrival[index]) continue;
    const cx = index % width;
    const cy = (index / width) | 0;
    for (const [ox, oy, distance] of neighborOffsets) {
      const nx = cx + ox;
      const ny = cy + oy;
      if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
      const ni = ny * width + nx;
      const fuel = terrain.fuel[ni];
      if (fuel <= 0) continue;
      const alignment = (ox * windX + oy * windY) / distance;
      const windFactor = Math.exp(1.15 * windStrength * alignment) * (alignment < 0 ? 0.85 : 1);
      const rise = (terrain.elevation[ni] - terrain.elevation[index]) * 40 / distance;
      const slopeFactor = Math.min(3, Math.max(0.35, Math.exp(rise)));
      const rate = 0.6 * fuel * moistureFactor * windFactor * slopeFactor * terrain.roughness[ni];
      const candidate = time + distance / Math.max(rate, 1e-4);
      if (candidate < arrival[ni]) {
        arrival[ni] = candidate;
        heap.push(candidate, ni);
      }
    }
  }

  let maxArrival = 0;
  for (let i = 0; i < size; i++) if (arrival[i] !== Infinity && arrival[i] > maxArrival) maxArrival = arrival[i];

  const run: FireRun = { params, terrain, arrival, maxArrival };
  if (runCache.size > 80) runCache.clear();
  runCache.set(key, run);
  return run;
}

/** Binary burned-extent mask at model time t. */
export function burnedMaskAt(run: FireRun, time: number): Uint8Array {
  const mask = new Uint8Array(run.arrival.length);
  for (let i = 0; i < mask.length; i++) mask[i] = run.arrival[i] <= time ? 1 : 0;
  return mask;
}

/** Deterministic ensemble: perturbs wind and moisture around a base scenario. */
export function buildIllustrativeEnsemble(base: FireScenarioParams, memberCount: number, seed = 42): FireRun[] {
  const random = createSeededRandom(seed);
  const runs: FireRun[] = [];
  for (let m = 0; m < memberCount; m++) {
    const directionJitter = (random() - 0.5) * 70;
    const speedJitter = (random() - 0.5) * 6;
    const moistureJitter = (random() - 0.5) * 0.16;
    runs.push(
      simulateFireSpread({
        ...base,
        windDirectionDeg: Math.round(base.windDirectionDeg + directionJitter),
        windSpeed: Math.max(0, Math.round((base.windSpeed + speedJitter) * 2) / 2),
        fuelMoisture: Math.max(0.02, Math.round((base.fuelMoisture + moistureJitter) * 100) / 100),
      }),
    );
  }
  return runs;
}

/** Shared base scenario used across the deck so visuals stay consistent. */
export const baseScenario: FireScenarioParams = {
  width: defaultGrid.width,
  height: defaultGrid.height,
  terrainSeed: 1337,
  windDirectionDeg: 70,
  windSpeed: 7,
  fuelMoisture: 0.12,
  ignitions: [[58, 62]],
};

/** Opening/closing cinematic scenario (ignition right of center, easterly spread). */
export const sparkScenario: FireScenarioParams = {
  width: 192,
  height: 108,
  terrainSeed: 1337,
  windDirectionDeg: 80,
  windSpeed: 9,
  fuelMoisture: 0.1,
  ignitions: [[118, 56]],
};
