/**
 * Presentation data contract. The deck renders only what this snapshot contains.
 * Every section is nullable: null means "awaiting verified results", never zero.
 */

export type EvidenceKind = "verified" | "simulatorDerived" | "illustration" | "proposed" | "unavailable";

export interface SourceReference {
  /** Path of the original artifact inside the experiment repository. */
  path: string;
  sha256?: string | null;
  ingestedAt?: string | null;
}

export type ImplementationStatus = "implemented" | "partial" | "proposed" | "unconfirmed";

export interface ComponentStatus {
  id: "simulation" | "dataset" | "surrogate" | "evaluation" | "orchestration" | "exploration";
  status: ImplementationStatus;
  sourceFiles: string[];
  note?: string | null;
}

export interface SimulatorInfo {
  name: string; // e.g. "ForeFire" or "Simplified cellular-automaton simulator"
  kind: "forefire" | "simplified" | "other";
  description: string;
  gridWidth: number | null;
  gridHeight: number | null;
  cellSizeMeters: number | null;
  horizonSteps: number | null;
  sourceFiles: string[];
  /** Optional recorded replay: frames of burned-extent row masks in time order. */
  replay?: {
    scenarioId: string;
    frameTimes: number[];
    timeUnit: string;
    frames: string[][];
    layers?: Record<string, number[][]>; // e.g. windU, windV, fuel, moisture, slope (0..1 normalized)
  } | null;
  source: SourceReference;
}

export interface DatasetInfo {
  totalScenarios: number | null;
  totalExamples: number | null;
  splits: { train: number | null; validation: number | null; test: number | null };
  splitUnit: "scenario" | "example";
  inputChannels: Array<{ name: string; description: string }>;
  target: string;
  resolution: { width: number; height: number } | null;
  /** Optional thumbnails of real extracted samples. */
  samples?: Array<{ id: string; channels: Record<string, string[]>; target: string[] }> | null;
  source: SourceReference;
}

export interface ModelInfo {
  modelType: string;
  parameterCount: number | null;
  inputResolution: string | null;
  outputResolution: string | null;
  inputChannels: number | null;
  device: string | null;
  checkpoint: string | null;
  definitionFile: string | null;
  training: {
    epochs: number | null;
    batchSize: number | null;
    optimizer: string | null;
    learningRate: number | null;
    loss: string | null;
    wallClockSeconds: number | null;
  };
  source: SourceReference;
}

export interface FidelityMetrics {
  iou: number | null;
  precision: number | null;
  recall: number | null;
  f2: number | null;
  burnedAreaError: number | null; // relative, signed
}

export interface FidelityExample {
  id: string;
  label: string;
  horizon: string | null;
  referenceMask?: string[] | null;
  predictionMask?: string[] | null;
  referenceImage?: string | null; // path under /public
  predictionImage?: string | null;
  errorImage?: string | null;
  metrics: FidelityMetrics | null;
}

export interface FidelityResults {
  split: string;
  sampleCount: number | null;
  horizon: string | null;
  aggregate: FidelityMetrics;
  baselines?: Array<{ name: string; metrics: FidelityMetrics }> | null;
  examples: FidelityExample[];
  source: SourceReference;
}

export type JobState = "completed" | "failed" | "cancelled" | "running" | "pending" | "unknown";

export interface WorkflowJob {
  id: string;
  name: string;
  stage: "simulation" | "dataset" | "training" | "evaluation" | "inference" | "other";
  start: string | null; // ISO timestamps
  end: string | null;
  state: JobState;
  dependsOn: string[];
  node: string | null;
  resources: { cpu?: number | null; gpu?: number | null; memoryGb?: number | null } | null;
  artifacts: string[];
}

export interface WorkflowExecution {
  workflowId: string;
  playback: "recorded"; // the deck never claims live monitoring
  recordedAt: string | null;
  executionMode: "sequential" | "overlapping" | "unknown";
  jobs: WorkflowJob[];
  screenshots?: string[] | null;
  source: SourceReference;
}

export interface MeasuredValue {
  value: number;
  unit: string;
  samples?: number | null;
  note?: string | null;
}

export interface BenchmarkResults {
  surrogateAcceleration: {
    simulatorSecondsPerScenario: MeasuredValue;
    surrogateSecondsPerScenario: MeasuredValue;
    batchSize: number | null;
    hardware: string | null;
    includesDataLoading: boolean | null;
  } | null;
  parallelThroughput: {
    oneNodeScenariosPerSecond: MeasuredValue;
    twoNodeScenariosPerSecond: MeasuredValue;
  } | null;
  workflowAcceleration: {
    sequentialSeconds: MeasuredValue;
    overlappingSeconds: MeasuredValue;
  } | null;
  trainingCost: { wallClockSeconds: MeasuredValue; device: string | null } | null;
  latencySamplesMs: number[] | null;
  utilization: Array<{ t: number; node: string; gpuPercent: number | null; cpuPercent: number | null }> | null;
  workflowBreakdown: Array<{ stage: string; seconds: number }> | null;
  source: SourceReference;
}

export interface EnsembleResults {
  memberCount: number;
  description: string;
  agreementMap: number[][] | null; // fraction of members burning per cell
  members: Array<{ id: string; label: string; mask: string[] }>;
  source: SourceReference;
}

export interface PresentationSnapshot {
  schemaVersion: 1;
  project: string;
  generatedAt: string | null;
  isFixture: boolean;
  components: ComponentStatus[];
  simulator: SimulatorInfo | null;
  dataset: DatasetInfo | null;
  model: ModelInfo | null;
  fidelity: FidelityResults | null;
  workflow: WorkflowExecution | null;
  benchmarks: BenchmarkResults | null;
  ensemble: EnsembleResults | null;
}

export type SectionName = "simulator" | "dataset" | "model" | "fidelity" | "workflow" | "benchmarks" | "ensemble";

/** Which upstream artifact each section is expected to come from (shown in awaiting states). */
export const expectedArtifacts: Record<SectionName, string> = {
  simulator: "simulator config + recorded replay (sim/*.json)",
  dataset: "data/manifest.json",
  model: "model metadata + models/best.pt",
  fidelity: "metrics/results.json",
  workflow: "Fuzzball workflow logs / status JSON",
  benchmarks: "benchmark CSV or JSON",
  ensemble: "ensemble outputs (only if executed)",
};
