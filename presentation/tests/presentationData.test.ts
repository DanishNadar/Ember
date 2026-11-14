import { describe, expect, it } from "vitest";
import { buildPresentationData } from "@/data/adapters/presentationData";
import verified from "@/data/verified/presentationSnapshot.json";
import fixture from "@/data/fixtures/sampleSnapshot.json";

describe("presentation data adapter", () => {
  it("treats the empty verified snapshot as awaiting everywhere (never zero)", () => {
    const data = buildPresentationData(verified);
    expect(data.availableSectionCount).toBe(0);
    expect(data.evidenceFor("fidelity")).toBe("unavailable");
    expect(data.evidenceFor("ensemble")).toBe("proposed");
    expect(data.surrogateSpeedup).toBeNull();
    expect(data.parallelScaling).toBeNull();
    expect(data.workflowSpeedup).toBeNull();
    expect(data.componentStatus("surrogate").status).toBe("unconfirmed");
  });

  it("classifies fixture sections as illustration, not verified", () => {
    const data = buildPresentationData(fixture);
    expect(data.isFixture).toBe(true);
    expect(data.evidenceFor("fidelity")).toBe("illustration");
    expect(data.issues).toEqual([]);
  });

  it("computes each ratio only when both measurements exist and keeps them separate", () => {
    const data = buildPresentationData(fixture);
    expect(data.surrogateSpeedup?.ratio).toBeCloseTo(4.2 / 0.0041, 3);
    expect(data.workflowSpeedup?.ratio).toBeCloseTo(4200 / 2940, 5);
    expect(data.parallelScaling).toBeNull(); // fixture has no two-node measurement
  });

  it("drops invalid sections and reports issues instead of guessing", () => {
    const broken = structuredClone(fixture) as Record<string, any>;
    broken.fidelity.aggregate.iou = 1.7;
    delete broken.benchmarks.source;
    broken.workflow.jobs[0].dependsOn = ["ghost-job"];
    const data = buildPresentationData(broken);
    expect(data.snapshot.fidelity).toBeNull();
    expect(data.snapshot.benchmarks).toBeNull();
    expect(data.snapshot.workflow).toBeNull();
    expect(data.issues.map((i) => i.section)).toEqual(expect.arrayContaining(["fidelity", "benchmarks", "workflow"]));
  });

  it("refuses non-recorded workflow playback", () => {
    const live = structuredClone(fixture) as Record<string, any>;
    live.workflow.playback = "live";
    expect(buildPresentationData(live).snapshot.workflow).toBeNull();
  });

  it("does not compute a speedup across mismatched units", () => {
    const mixed = structuredClone(fixture) as Record<string, any>;
    mixed.benchmarks.surrogateAcceleration.surrogateSecondsPerScenario.unit = "ms";
    const data = buildPresentationData(mixed);
    expect(data.surrogateSpeedup).toBeNull();
  });
});
