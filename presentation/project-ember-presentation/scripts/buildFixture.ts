/**
 * Generates data/fixtures/sampleSnapshot.json — an ILLUSTRATIVE FIXTURE used to preview
 * and test result layouts before real artifacts exist. Every number here is synthetic.
 * The deck shows a persistent "Illustrative fixture" watermark whenever it is loaded.
 *
 * Run: npx tsx scripts/buildFixture.ts
 */
import { writeFileSync } from "node:fs";
import { simulateFireSpread, burnedMaskAt, type FireScenarioParams } from "../lib/fireModel";
import { computeMaskAgreement, encodeRowMask } from "../lib/maskMetrics";
import { createSeededRandom } from "../lib/seededRandom";

const size = 64;
const random = createSeededRandom(2026);

function perturbPrediction(reference: Uint8Array, quality: number): Uint8Array {
  // Synthetic "prediction": randomly flips cells on the fire boundary, more often when quality is low.
  const out = new Uint8Array(reference);
  for (let y = 1; y < size - 1; y++) {
    for (let x = 1; x < size - 1; x++) {
      const i = y * size + x;
      const neighbors = reference[i - 1] + reference[i + 1] + reference[i - size] + reference[i + size];
      const onBoundary = neighbors > 0 && neighbors < 4;
      if (onBoundary && random() > quality) out[i] = reference[i] ? 0 : 1;
      if (!reference[i] && neighbors >= 2 && random() > quality + 0.15) out[i] = 1;
    }
  }
  return out;
}

const scenarios: Array<{ id: string; label: string; params: Partial<FireScenarioParams>; quality: number; horizonFraction: number }> = [
  { id: "test-0007", label: "Moderate east wind", params: { windDirectionDeg: 90, windSpeed: 6 }, quality: 0.86, horizonFraction: 0.3 },
  { id: "test-0013", label: "Hard case: calm, dry fuels", params: { windDirectionDeg: 0, windSpeed: 1, fuelMoisture: 0.05 }, quality: 0.92, horizonFraction: 0.28 },
  { id: "test-0021", label: "Strong north-east wind", params: { windDirectionDeg: 45, windSpeed: 14 }, quality: 0.8, horizonFraction: 0.3 },
  { id: "test-0034", label: "Wet fuels, shifting wind", params: { windDirectionDeg: 200, windSpeed: 9, fuelMoisture: 0.3 }, quality: 0.45, horizonFraction: 0.32 },
];

const examples = scenarios.map((s) => {
  const run = simulateFireSpread({
    width: size, height: size, terrainSeed: 77, windDirectionDeg: 90, windSpeed: 6, fuelMoisture: 0.12,
    ignitions: [[28, 34]], ...s.params,
  });
  const horizon = run.maxArrival * s.horizonFraction;
  const reference = burnedMaskAt(run, horizon);
  // Synthetic surrogate error: a run with biased wind, evaluated at the same horizon, plus boundary noise.
  const biased = simulateFireSpread({ ...run.params, windDirectionDeg: run.params.windDirectionDeg + (1 - s.quality) * 90, windSpeed: run.params.windSpeed * (0.6 + s.quality * 0.4) });
  const prediction = perturbPrediction(burnedMaskAt(biased, horizon * (0.8 + s.quality * 0.2)), s.quality);
  const m = computeMaskAgreement(reference, prediction);
  return {
    id: s.id,
    label: s.label,
    horizon: "t + 12 steps (fixture)",
    referenceMask: encodeRowMask(reference, size, size),
    predictionMask: encodeRowMask(prediction, size, size),
    metrics: { iou: m.iou, precision: m.precision, recall: m.recall, f2: m.f2, burnedAreaError: m.burnedAreaError },
  };
});

const mean = (key: "iou" | "precision" | "recall" | "f2" | "burnedAreaError") =>
  examples.reduce((sum, e) => sum + (e.metrics[key] ?? 0), 0) / examples.length;

const replayRun = simulateFireSpread({
  width: size, height: size, terrainSeed: 77, windDirectionDeg: 80, windSpeed: 7, fuelMoisture: 0.1, ignitions: [[20, 36]],
});
const frameTimes = Array.from({ length: 12 }, (_, k) => Math.round((replayRun.maxArrival * 0.7 * k) / 11));
const replayFrames = frameTimes.map((t) => encodeRowMask(burnedMaskAt(replayRun, t), size, size));
const fuelLayer: number[][] = [];
const slopeLayer: number[][] = [];
for (let y = 0; y < size; y++) {
  fuelLayer.push(Array.from({ length: size }, (_, x) => +replayRun.terrain.fuel[y * size + x].toFixed(2)));
  slopeLayer.push(Array.from({ length: size }, (_, x) => +Math.min(1, replayRun.terrain.slope[y * size + x]).toFixed(2)));
}

const t0 = Date.parse("2026-11-14T09:00:00Z");
const at = (minutes: number) => new Date(t0 + minutes * 60_000).toISOString();
const jobs = [
  ...[0, 1, 2, 3].map((k) => ({
    id: `simulate-batch-${k}`, name: `Simulate batch ${k}`, stage: "simulation", start: at(k * 9), end: at(k * 9 + 10),
    state: "completed", dependsOn: k === 0 ? [] : [`simulate-batch-${k - 1}`], node: "node-a",
    resources: { cpu: 16, gpu: 0, memoryGb: 32 }, artifacts: [`data/shards/shard-${k}.npz`],
  })),
  { id: "build-dataset", name: "Build dataset", stage: "dataset", start: at(10), end: at(13), state: "completed", dependsOn: ["simulate-batch-0"], node: "node-b", resources: { cpu: 8, gpu: 0, memoryGb: 16 }, artifacts: ["data/manifest.json"] },
  { id: "train-surrogate", name: "Train surrogate", stage: "training", start: at(13), end: at(44), state: "completed", dependsOn: ["build-dataset"], node: "node-b", resources: { cpu: 8, gpu: 1, memoryGb: 64 }, artifacts: ["models/best.pt"] },
  { id: "evaluate", name: "Evaluate held-out", stage: "evaluation", start: at(45), end: at(49), state: "completed", dependsOn: ["train-surrogate", "simulate-batch-3"], node: "node-b", resources: { cpu: 4, gpu: 1, memoryGb: 16 }, artifacts: ["metrics/results.json", "outputs/comparison.png"] },
];

const latency: number[] = Array.from({ length: 200 }, () => +(3.1 + Math.abs(random() + random() + random() - 1.5) * 1.6).toFixed(3));

const snapshot = {
  schemaVersion: 1,
  project: "Project Ember — Adaptive Wildfire Surrogate",
  generatedAt: new Date(t0).toISOString(),
  isFixture: true,
  components: [
    { id: "simulation", status: "implemented", sourceFiles: ["sim/run_simulations.py"], note: "fixture" },
    { id: "dataset", status: "implemented", sourceFiles: ["data/build_dataset.py"], note: "fixture" },
    { id: "surrogate", status: "implemented", sourceFiles: ["model/unet.py", "train.py"], note: "fixture" },
    { id: "evaluation", status: "implemented", sourceFiles: ["evaluate.py"], note: "fixture" },
    { id: "orchestration", status: "partial", sourceFiles: ["fuzzball/ember.yaml"], note: "fixture" },
    { id: "exploration", status: "proposed", sourceFiles: [], note: "fixture" },
  ],
  simulator: {
    name: "Fixture simulator", kind: "simplified",
    description: "Synthetic replay generated by the deck's illustrative spread model (fixture only).",
    gridWidth: size, gridHeight: size, cellSizeMeters: 30, horizonSteps: 12, sourceFiles: ["fixture"],
    replay: { scenarioId: "fixture-replay", frameTimes, timeUnit: "steps", frames: replayFrames, layers: { fuel: fuelLayer, slope: slopeLayer } },
    source: { path: "data/fixtures/sampleSnapshot.json" },
  },
  dataset: {
    totalScenarios: 480, totalExamples: 5760, splits: { train: 384, validation: 48, test: 48 }, splitUnit: "scenario",
    inputChannels: [
      { name: "burnedMask", description: "Initial burned-area mask" },
      { name: "windU", description: "Wind east-west component" },
      { name: "windV", description: "Wind north-south component" },
      { name: "fuel", description: "Fuel load / type index" },
      { name: "moisture", description: "Fuel moisture" },
      { name: "slope", description: "Terrain slope" },
    ],
    target: "Burned-area mask at t + horizon", resolution: { width: size, height: size }, samples: null,
    source: { path: "data/fixtures/sampleSnapshot.json" },
  },
  model: {
    modelType: "U-Net (fixture)", parameterCount: 1_940_000, inputResolution: "6 × 64 × 64", outputResolution: "1 × 64 × 64",
    inputChannels: 6, device: "fixture device", checkpoint: "models/best.pt", definitionFile: "model/unet.py",
    training: { epochs: 30, batchSize: 64, optimizer: "AdamW", learningRate: 0.001, loss: "BCE + Dice", wallClockSeconds: 1860 },
    source: { path: "data/fixtures/sampleSnapshot.json" },
  },
  fidelity: {
    split: "test", sampleCount: 48, horizon: "t + 12 steps",
    aggregate: { iou: mean("iou"), precision: mean("precision"), recall: mean("recall"), f2: mean("f2"), burnedAreaError: mean("burnedAreaError") },
    baselines: [{ name: "Persistence (no spread)", metrics: { iou: 0.41, precision: 0.99, recall: 0.41, f2: 0.46, burnedAreaError: -0.59 } }],
    examples,
    source: { path: "data/fixtures/sampleSnapshot.json" },
  },
  workflow: {
    workflowId: "wf-fixture-0001", playback: "recorded", recordedAt: at(50), executionMode: "overlapping", jobs, screenshots: null,
    source: { path: "data/fixtures/sampleSnapshot.json" },
  },
  benchmarks: {
    surrogateAcceleration: {
      simulatorSecondsPerScenario: { value: 4.2, unit: "s", samples: 48 },
      surrogateSecondsPerScenario: { value: 0.0041, unit: "s", samples: 200 },
      batchSize: 1, hardware: "fixture", includesDataLoading: false,
    },
    parallelThroughput: null,
    workflowAcceleration: { sequentialSeconds: { value: 4200, unit: "s" }, overlappingSeconds: { value: 2940, unit: "s" } },
    trainingCost: { wallClockSeconds: { value: 1860, unit: "s" }, device: "fixture" },
    latencySamplesMs: latency,
    utilization: Array.from({ length: 40 }, (_, k) => ({ t: k * 75, node: k % 2 ? "node-b" : "node-a", gpuPercent: k % 2 ? 60 + (k % 7) * 4 : 2, cpuPercent: k % 2 ? 30 : 85 - (k % 5) * 3 })),
    workflowBreakdown: [
      { stage: "simulation", seconds: 2400 }, { stage: "dataset", seconds: 180 }, { stage: "training", seconds: 1860 }, { stage: "evaluation", seconds: 240 },
    ],
    source: { path: "data/fixtures/sampleSnapshot.json" },
  },
  ensemble: null,
};

writeFileSync(new URL("../data/fixtures/sampleSnapshot.json", import.meta.url), JSON.stringify(snapshot));
console.log("fixture written; aggregate IoU", snapshot.fidelity.aggregate.iou.toFixed(3));
