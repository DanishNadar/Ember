/** Binary-mask agreement metrics. Used to recompute per-example scores from stored masks. */
export interface MaskAgreement {
  iou: number | null;
  precision: number | null;
  recall: number | null;
  f2: number | null;
  burnedAreaError: number | null; // relative: (predicted - reference) / reference
  truePositive: number;
  falsePositive: number;
  falseNegative: number;
}

export function computeMaskAgreement(reference: ArrayLike<number>, prediction: ArrayLike<number>): MaskAgreement {
  if (reference.length !== prediction.length) {
    throw new Error(`Mask size mismatch: ${reference.length} vs ${prediction.length}`);
  }
  let tp = 0;
  let fp = 0;
  let fn = 0;
  for (let i = 0; i < reference.length; i++) {
    const r = reference[i] ? 1 : 0;
    const p = prediction[i] ? 1 : 0;
    if (r && p) tp++;
    else if (p) fp++;
    else if (r) fn++;
  }
  const ratio = (num: number, den: number) => (den === 0 ? null : num / den);
  const precision = ratio(tp, tp + fp);
  const recall = ratio(tp, tp + fn);
  const f2 = precision === null || recall === null || precision + recall === 0
    ? null
    : (5 * precision * recall) / (4 * precision + recall);
  const referenceArea = tp + fn;
  const predictedArea = tp + fp;
  return {
    iou: ratio(tp, tp + fp + fn),
    precision,
    recall,
    f2,
    burnedAreaError: referenceArea === 0 ? null : (predictedArea - referenceArea) / referenceArea,
    truePositive: tp,
    falsePositive: fp,
    falseNegative: fn,
  };
}

/** Decodes a mask stored as an array of "0101..." row strings. */
export function decodeRowMask(rows: string[]): { width: number; height: number; mask: Uint8Array } {
  const height = rows.length;
  const width = height > 0 ? rows[0].length : 0;
  const mask = new Uint8Array(width * height);
  rows.forEach((row, y) => {
    for (let x = 0; x < width; x++) mask[y * width + x] = row.charCodeAt(x) === 49 ? 1 : 0;
  });
  return { width, height, mask };
}

export function encodeRowMask(mask: ArrayLike<number>, width: number, height: number): string[] {
  const rows: string[] = [];
  for (let y = 0; y < height; y++) {
    let row = "";
    for (let x = 0; x < width; x++) row += mask[y * width + x] ? "1" : "0";
    rows.push(row);
  }
  return rows;
}
