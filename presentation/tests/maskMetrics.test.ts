import { describe, expect, it } from "vitest";
import { computeMaskAgreement, decodeRowMask, encodeRowMask } from "@/lib/maskMetrics";

describe("mask metrics", () => {
  it("computes IoU, precision, recall, F2 and area error", () => {
    const ref = [1, 1, 1, 1, 0, 0, 0, 0];
    const pred = [1, 1, 1, 0, 1, 0, 0, 0];
    const m = computeMaskAgreement(ref, pred);
    expect(m.iou).toBeCloseTo(3 / 5);
    expect(m.precision).toBeCloseTo(3 / 4);
    expect(m.recall).toBeCloseTo(3 / 4);
    expect(m.f2).toBeCloseTo(0.75);
    expect(m.burnedAreaError).toBeCloseTo(0);
  });
  it("returns null (not zero) for undefined ratios", () => {
    const m = computeMaskAgreement([0, 0], [0, 0]);
    expect(m.iou).toBeNull();
    expect(m.precision).toBeNull();
    expect(m.burnedAreaError).toBeNull();
  });
  it("round-trips row-string masks", () => {
    const rows = ["0110", "1001"];
    const { mask, width, height } = decodeRowMask(rows);
    expect(encodeRowMask(mask, width, height)).toEqual(rows);
  });
  it("rejects size mismatches", () => {
    expect(() => computeMaskAgreement([1], [1, 0])).toThrow();
  });
});
