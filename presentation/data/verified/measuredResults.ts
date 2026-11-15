/**
 * Measured results from the team's Nov 15, 2026 test runs, transcribed from the
 * overnight integration handoff. Every number here traces to a run artifact.
 * Keep the caveats with the numbers: accuracy = agreement with ForeFire simulator labels,
 * not real-world wildfire forecast skill.
 */

export const dataset = {
  candidateScenarios: 26_000, // prepared input conditions, NOT completed simulations
  train: 2_400,
  validation: 300,
  test: 180,
  channels: 19,
  grid: 320,
  cellMeters: 40,
  horizonMinutes: 60,
  regions: ["Corsica", "Southern California", "Northern California", "Great Basin"],
  simulator: "ForeFire 2.6.0",
} as const;

/**
 * First prototype: smaller, single-region dataset. Validation numbers on 32 scenarios.
 * Not a controlled comparison with the scaled model (different channels, regions, split, sizes).
 */
export const prototype = {
  scenariosAttempted: 512,
  scenariosPassed: 508,
  region: "Texas",
  channels: 22,
  epochs: 30,
  bestEpoch: 29,
  evalSamples: 32,
  iou: 0.4903,
  arrivalMaeSeconds: 630.4,
  emptyPredictions: 0,
  trainMinutes: 15.21,
} as const;

/** Winning two-head U-Net on the 180-sample held-out ForeFire test (an earlier evaluation run, separate from runs 1–4). */
export const surrogate = {
  testSamples: 180,
  iou: 0.47965,
  dice: 0.64833,
  precision: 0.78401,
  recall: 0.55268,
  arrivalMaeSeconds: 428.0,
  threshold: 0.4,
  epochs: 40,
  trainMinutes: 11.4,
  checkpointMB: 1.9,
} as const;

/** Full two-phase, two-node pipeline (run 4). */
export const twoNodeRun = {
  elapsed: "1m 40s",
  nodes: [
    { name: "Node A", rank: 0, overlapSeconds: 7.05, phaseSeconds: 20.4 },
    { name: "Node B", rank: 1, overlapSeconds: 7.66, phaseSeconds: 15.18 },
  ],
  stagedTrain: 48,
  newLabels: 126,
  mergedTrain: 174,
  backend: "NCCL",
  worldSize: 2,
  weightSha: "6c1660c6…903c87",
  smokeTest: { samples: 12, iou: 0.5184, dice: 0.6829 },
} as const;

/** How we got there: the runs that mark each step, including the failure. */
export const milestones = [
  { run: 1, label: "Trained model runs on a GPU", ok: true },
  { run: 2, label: "One node: physics + GPU training together", ok: true },
  { run: 3, label: "Two nodes ran, merge rejected a duplicate label", ok: false },
  { run: 4, label: "Full two-node pipeline, synchronized weights", ok: true },
] as const;

export const struggles = [
  {
    problem: "No off-site access to the Fuzzball cluster",
    fix: "Built and proved each stage in small test runs first, and staged the Fuzzball workflow for the on-site GB10s.",
  },
  {
    problem: "Physics and AI need different Python stacks",
    fix: "A split-interpreter launcher gives ForeFire and PyTorch their own runtime, side by side on the same node.",
  },
  {
    problem: "The merge rejected a duplicate physics label",
    fix: "We kept the strict check and fixed shard assignment to skip existing IDs. The next run passed end to end.",
  },
  {
    problem: "Shared storage mount: permission denied",
    fix: "Switched to node-local scratch volumes with an explicit, hash-checked artifact handoff.",
  },
] as const;
