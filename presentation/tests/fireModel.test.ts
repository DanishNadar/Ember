import { describe, expect, it } from "vitest";
import { baseScenario, generateTerrain, simulateFireSpread, sparkScenario } from "@/lib/fireModel";

describe("illustrative fire model", () => {
  it("is deterministic", () => {
    const a = simulateFireSpread({ ...baseScenario, windSpeed: 9.5 });
    const b = simulateFireSpread({ ...baseScenario, windSpeed: 9.5, ignitions: [...baseScenario.ignitions] });
    expect(Array.from(a.arrival.slice(0, 500))).toEqual(Array.from(b.arrival.slice(0, 500)));
  });
  it("spreads further downwind", () => {
    const run = simulateFireSpread({ ...baseScenario, windDirectionDeg: 90, windSpeed: 12 });
    const [x, y] = baseScenario.ignitions[0];
    const w = baseScenario.width;
    expect(run.arrival[y * w + x + 20]).toBeLessThan(run.arrival[y * w + x - 20]);
  });
  it("never ignites on water for the scenarios used in the deck", () => {
    for (const s of [baseScenario, sparkScenario]) {
      const t = generateTerrain(s.terrainSeed, s.width, s.height);
      const [x, y] = s.ignitions[0];
      expect(t.water[y * s.width + x]).toBe(0);
    }
  });
});
