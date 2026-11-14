/**
 * Marching-squares isolines over a scalar grid, returned as flat segment arrays
 * [x1, y1, x2, y2, ...] in grid units. Used for smooth fire fronts and terrain contours.
 */

/** Separable box blur; non-finite cells are clamped to `fillValue` first. */
export function blurField(values: ArrayLike<number>, width: number, height: number, radius: number, fillValue: number): Float32Array {
  const src = new Float32Array(width * height);
  for (let i = 0; i < src.length; i++) src[i] = Number.isFinite(values[i]) ? values[i] : fillValue;
  if (radius <= 0) return src;
  const tmp = new Float32Array(src.length);
  const out = new Float32Array(src.length);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let sum = 0;
      let n = 0;
      for (let k = -radius; k <= radius; k++) {
        const xx = Math.min(width - 1, Math.max(0, x + k));
        sum += src[y * width + xx];
        n++;
      }
      tmp[y * width + x] = sum / n;
    }
  }
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let sum = 0;
      let n = 0;
      for (let k = -radius; k <= radius; k++) {
        const yy = Math.min(height - 1, Math.max(0, y + k));
        sum += tmp[yy * width + x];
        n++;
      }
      out[y * width + x] = sum / n;
    }
  }
  return out;
}

export function isolineSegments(field: Float32Array, width: number, height: number, level: number): number[] {
  const segments: number[] = [];
  const lerp = (a: number, b: number) => (level - a) / (b - a || 1e-9);
  for (let y = 0; y < height - 1; y++) {
    for (let x = 0; x < width - 1; x++) {
      const tl = field[y * width + x];
      const tr = field[y * width + x + 1];
      const br = field[(y + 1) * width + x + 1];
      const bl = field[(y + 1) * width + x];
      const code = (tl > level ? 8 : 0) | (tr > level ? 4 : 0) | (br > level ? 2 : 0) | (bl > level ? 1 : 0);
      if (code === 0 || code === 15) continue;
      const top: [number, number] = [x + lerp(tl, tr), y];
      const right: [number, number] = [x + 1, y + lerp(tr, br)];
      const bottom: [number, number] = [x + lerp(bl, br), y + 1];
      const left: [number, number] = [x, y + lerp(tl, bl)];
      const push = (a: [number, number], b: [number, number]) => segments.push(a[0], a[1], b[0], b[1]);
      switch (code) {
        case 1: case 14: push(left, bottom); break;
        case 2: case 13: push(bottom, right); break;
        case 3: case 12: push(left, right); break;
        case 4: case 11: push(top, right); break;
        case 5: push(left, top); push(bottom, right); break;
        case 6: case 9: push(top, bottom); break;
        case 7: case 8: push(left, top); break;
        case 10: push(left, bottom); push(top, right); break;
      }
    }
  }
  return segments;
}

/** Draws segments scaled from grid units to canvas pixels. */
export function strokeSegments(ctx: CanvasRenderingContext2D, segments: number[], sx: number, sy: number) {
  ctx.beginPath();
  for (let i = 0; i < segments.length; i += 4) {
    ctx.moveTo(segments[i] * sx + sx / 2, segments[i + 1] * sy + sy / 2);
    ctx.lineTo(segments[i + 2] * sx + sx / 2, segments[i + 3] * sy + sy / 2);
  }
  ctx.stroke();
}

const contourCache = new WeakMap<object, number[]>();

/** Cached terrain contour lines at evenly spaced elevation levels. */
export function terrainContours(key: object, elevation: Float32Array, width: number, height: number, levels = 12): number[] {
  const cached = contourCache.get(key);
  if (cached) return cached;
  const smooth = blurField(elevation, width, height, 1, 0);
  const all: number[] = [];
  for (let k = 1; k < levels; k++) all.push(...isolineSegments(smooth, width, height, 0.2 + (k / levels) * 0.6));
  contourCache.set(key, all);
  return all;
}

/**
 * Hole-free burned footprint at time t: cells not reachable from the grid border through
 * unburned cells count as inside. Returns a 0/1 Float32Array suitable for isolines at 0.5.
 */
export function filledFootprint(arrival: Float32Array, width: number, height: number, time: number): Float32Array {
  const size = width * height;
  const outside = new Uint8Array(size);
  const stack: number[] = [];
  const visit = (i: number) => {
    if (!outside[i] && arrival[i] > time) {
      outside[i] = 1;
      stack.push(i);
    }
  };
  for (let x = 0; x < width; x++) {
    visit(x);
    visit((height - 1) * width + x);
  }
  for (let y = 0; y < height; y++) {
    visit(y * width);
    visit(y * width + width - 1);
  }
  while (stack.length) {
    const i = stack.pop()!;
    const x = i % width;
    if (x > 0) visit(i - 1);
    if (x < width - 1) visit(i + 1);
    if (i >= width) visit(i - width);
    if (i < size - width) visit(i + width);
  }
  const filled = new Float32Array(size);
  for (let i = 0; i < size; i++) filled[i] = outside[i] ? 0 : 1;
  return filled;
}
