/** Deterministic PRNG (mulberry32) so every animation replays identically. */
export function createSeededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return function nextRandom() {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Integer hash of a lattice point, mapped to [0, 1). */
function hashLattice(x: number, y: number, seed: number): number {
  let h = (x * 374761393 + y * 668265263 + seed * 2147483647) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}

function smoothStep(t: number): number {
  return t * t * (3 - 2 * t);
}

/** Bilinear value noise in [0, 1). */
export function valueNoise(x: number, y: number, seed: number): number {
  const xi = Math.floor(x);
  const yi = Math.floor(y);
  const fx = smoothStep(x - xi);
  const fy = smoothStep(y - yi);
  const a = hashLattice(xi, yi, seed);
  const b = hashLattice(xi + 1, yi, seed);
  const c = hashLattice(xi, yi + 1, seed);
  const d = hashLattice(xi + 1, yi + 1, seed);
  return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
}

/** Fractal Brownian motion: layered value noise for natural-looking terrain. */
export function fractalNoise(x: number, y: number, seed: number, octaves = 5): number {
  let amplitude = 0.5;
  let frequency = 1;
  let sum = 0;
  let norm = 0;
  for (let octave = 0; octave < octaves; octave++) {
    sum += amplitude * valueNoise(x * frequency, y * frequency, seed + octave * 101);
    norm += amplitude;
    amplitude *= 0.5;
    frequency *= 2.03;
  }
  return sum / norm;
}
