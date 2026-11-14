import { describe, expect, it } from "vitest";
import { layerStatus, stackLayers, judgingCriteria } from "@/lib/ecosystem";
import { buildPresentationData } from "@/data/adapters/presentationData";
import verified from "@/data/verified/presentationSnapshot.json";
import fixture from "@/data/fixtures/sampleSnapshot.json";
import { emberFuzzfileLines, emberFuzzfileText } from "@/lib/emberFuzzfile";

describe("ecosystem status", () => {
  it("never shows 'verified' without ingested workflow logs", () => {
    const { snapshot } = buildPresentationData(verified);
    for (const layer of stackLayers) expect(layerStatus(layer.id, snapshot).status).not.toBe("verified");
  });
  it("does not let fixture data upgrade anything to verified", () => {
    const { snapshot } = buildPresentationData(fixture);
    expect(layerStatus("orchestrate", snapshot).status).not.toBe("verified");
  });
  it("upgrades Orchestrate/Substrate and hardware from real logs", () => {
    const real = { ...structuredClone(fixture), isFixture: false };
    const { snapshot } = buildPresentationData(real);
    expect(layerStatus("orchestrate", snapshot).status).toBe("verified");
    expect(layerStatus("hardware", snapshot).status).toBe("verified"); // fixture jobs span node-a and node-b
    expect(layerStatus("storage", snapshot).status).toBe("unconfirmed"); // VAST never inferred
  });
  it("carries the four official criteria", () => {
    expect(judgingCriteria.map((c) => c.title)).toEqual([
      "Technical Execution & Completeness", "Ecosystem Utility", "Value & Impact", "Innovation & Execution",
    ]);
  });
  it("Fuzzfile template uses v4 syntax and the documented keys", () => {
    expect(emberFuzzfileText).toContain("version: v4");
    for (const key of ["task-array:", "depends-on:", "status: RUNNING", "nvidia.com/gpu: 1", "use: persistent"]) {
      expect(emberFuzzfileText).toContain(key);
    }
    expect(emberFuzzfileLines.every((l) => l.text.length <= 60)).toBe(true);
  });
});
