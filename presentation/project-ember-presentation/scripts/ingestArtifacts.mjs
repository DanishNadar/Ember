#!/usr/bin/env node
/**
 * Ingests experiment artifacts into data/verified/presentationSnapshot.json.
 *
 *   EMBER_REPO=/path/to/ember npm run ingest
 *   node scripts/ingestArtifacts.mjs --repo /path/to/ember [--config data/adapters/artifactConfig.json] [--dry-run]
 *
 * Rules:
 *  - Never invents values. A key that can't be found stays null; a missing file leaves its section null.
 *  - Never modifies the experiment repository. Images listed in copyAssets are COPIED into public/experiment-assets.
 *  - Every section records the source path and SHA-256 of the artifact it came from.
 */
import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(here, "..");
const args = process.argv.slice(2);
const argValue = (flag) => {
  const i = args.indexOf(flag);
  return i >= 0 ? args[i + 1] : undefined;
};
const repo = path.resolve(argValue("--repo") ?? process.env.EMBER_REPO ?? ".");
const configPath = path.resolve(projectRoot, argValue("--config") ?? "data/adapters/artifactConfig.json");
const dryRun = args.includes("--dry-run");
const outPath = path.resolve(projectRoot, argValue("--out") ?? "data/verified/presentationSnapshot.json");
const config = JSON.parse(readFileSync(configPath, "utf8"));
const now = new Date().toISOString();
const log = (...m) => console.log("[ingest]", ...m);

function locate(key) {
  for (const rel of config[key] ?? []) {
    const abs = path.join(repo, rel);
    if (existsSync(abs)) return { rel, abs };
  }
  return null;
}
function sourceRef(found) {
  const sha256 = createHash("sha256").update(readFileSync(found.abs)).digest("hex");
  return { path: found.rel, sha256, ingestedAt: now };
}
function readJson(found) {
  return JSON.parse(readFileSync(found.abs, "utf8"));
}
/** First defined value among candidate keys (supports dotted paths). */
function pick(obj, ...keys) {
  for (const key of keys) {
    const value = key.split(".").reduce((o, k) => (o && typeof o === "object" ? o[k] : undefined), obj);
    if (value !== undefined && value !== null) return value;
  }
  return null;
}
const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v)) ? Number(v) : null);
const count = (v) => (Array.isArray(v) ? v.length : num(v));

function maskRows(value) {
  // Accepts ["0101", ...] or [[0,1,0,1], ...]; anything else → null.
  if (!Array.isArray(value) || value.length === 0) return null;
  if (typeof value[0] === "string") return value;
  if (Array.isArray(value[0])) return value.map((row) => row.map((c) => (Number(c) >= 0.5 ? "1" : "0")).join(""));
  return null;
}

function metricsFrom(obj) {
  if (!obj || typeof obj !== "object") return null;
  return {
    iou: num(pick(obj, "iou", "IoU", "mean_iou", "fire_iou", "test_iou")),
    precision: num(pick(obj, "precision", "test_precision")),
    recall: num(pick(obj, "recall", "test_recall")),
    f2: num(pick(obj, "f2", "F2", "f2_score")),
    burnedAreaError: num(pick(obj, "burnedAreaError", "burned_area_error", "area_error", "relative_area_error")),
  };
}

const snapshot = existsSync(outPath) ? JSON.parse(readFileSync(outPath, "utf8")) : {};
const next = {
  schemaVersion: 1,
  project: "Project Ember — Adaptive Wildfire Surrogate",
  generatedAt: now,
  isFixture: false,
  components: [],
  simulator: null, dataset: null, model: null, fidelity: null, workflow: null, benchmarks: null, ensemble: null,
  workflowDefinition: null,
};

// The team's real Fuzzfile, shown verbatim on the "workflow as code" slide.
const fuzzfile = locate("fuzzfile");
if (fuzzfile) {
  next.workflowDefinition = { path: fuzzfile.rel, text: readFileSync(fuzzfile.abs, "utf8"), source: sourceRef(fuzzfile) };
  log("fuzzfile ←", fuzzfile.rel);
}

// Team-declared ecosystem usage (copied, never inferred).
const ecosystemFile = locate("ecosystemUsage");
if (ecosystemFile && !dryRun) {
  copyFileSync(ecosystemFile.abs, path.join(projectRoot, "data/verified/ecosystemUsage.json"));
  log("ecosystem usage ←", ecosystemFile.rel);
}

// Components (implementation status) — only from an explicit file written by the team.
const componentsFile = locate("components");
if (componentsFile) next.components = readJson(componentsFile);

// Fidelity
const resultsFile = locate("results");
if (resultsFile) {
  const r = readJson(resultsFile);
  const aggregateSource = pick(r, "aggregate", "test", "metrics", "overall") ?? r;
  const examples = (pick(r, "examples", "per_example", "samples") ?? []).map((ex, k) => ({
    id: String(pick(ex, "id", "scenario_id", "name") ?? `example-${k}`),
    label: String(pick(ex, "label", "description", "id", "scenario_id") ?? `Example ${k + 1}`),
    horizon: pick(ex, "horizon") ?? null,
    referenceMask: maskRows(pick(ex, "referenceMask", "reference_mask", "target_mask", "target")),
    predictionMask: maskRows(pick(ex, "predictionMask", "prediction_mask", "pred_mask", "prediction")),
    referenceImage: pick(ex, "referenceImage", "reference_image") ?? null,
    predictionImage: pick(ex, "predictionImage", "prediction_image") ?? null,
    errorImage: pick(ex, "errorImage", "error_image") ?? null,
    metrics: metricsFrom(pick(ex, "metrics") ?? ex),
  }));
  next.fidelity = {
    split: String(pick(r, "split") ?? "test"),
    sampleCount: num(pick(r, "sampleCount", "n", "num_samples", "count")),
    horizon: pick(r, "horizon") ?? null,
    aggregate: metricsFrom(aggregateSource),
    baselines: Array.isArray(r.baselines) ? r.baselines.map((b) => ({ name: String(b.name), metrics: metricsFrom(b.metrics ?? b) })) : null,
    examples,
    source: sourceRef(resultsFile),
  };
  log("fidelity ←", resultsFile.rel, `(${examples.length} examples)`);
}

// Dataset
const manifestFile = locate("manifest");
if (manifestFile) {
  const m = readJson(manifestFile);
  const splits = pick(m, "splits", "split") ?? {};
  const channels = pick(m, "inputChannels", "input_channels", "channels") ?? [];
  const res = pick(m, "resolution", "grid");
  next.dataset = {
    totalScenarios: count(pick(m, "totalScenarios", "total_scenarios", "num_scenarios", "scenarios")),
    totalExamples: count(pick(m, "totalExamples", "total_examples", "num_examples", "examples")),
    splits: {
      train: count(pick(splits, "train")),
      validation: count(pick(splits, "validation", "val", "valid")),
      test: count(pick(splits, "test")),
    },
    splitUnit: pick(m, "splitUnit", "split_unit") ?? "scenario",
    inputChannels: channels.map((c) => (typeof c === "string" ? { name: c, description: c } : { name: String(c.name), description: String(c.description ?? c.name) })),
    target: String(pick(m, "target", "target_description") ?? "burned-area mask at horizon"),
    resolution: res && num(res.width ?? res[1]) ? { width: num(res.width ?? res[1]), height: num(res.height ?? res[0]) } : null,
    samples: null,
    source: sourceRef(manifestFile),
  };
  log("dataset ←", manifestFile.rel);
}

// Model
const modelFile = locate("modelMetadata");
const checkpointFile = locate("checkpoint");
if (modelFile) {
  const m = readJson(modelFile);
  const shape = (v) => (Array.isArray(v) ? v.join(" × ") : v ?? null);
  next.model = {
    modelType: String(pick(m, "modelType", "model_type", "architecture", "name") ?? "unspecified"),
    parameterCount: num(pick(m, "parameterCount", "parameter_count", "num_params", "params")),
    inputResolution: shape(pick(m, "inputResolution", "input_shape", "input_resolution")),
    outputResolution: shape(pick(m, "outputResolution", "output_shape", "output_resolution")),
    inputChannels: num(pick(m, "inputChannels", "in_channels")),
    device: pick(m, "device", "gpu") ?? null,
    checkpoint: checkpointFile?.rel ?? pick(m, "checkpoint") ?? null,
    definitionFile: pick(m, "definitionFile", "definition_file", "model_file") ?? null,
    training: {
      epochs: num(pick(m, "training.epochs", "epochs")),
      batchSize: num(pick(m, "training.batchSize", "training.batch_size", "batch_size")),
      optimizer: pick(m, "training.optimizer", "optimizer") ?? null,
      learningRate: num(pick(m, "training.learningRate", "training.lr", "learning_rate", "lr")),
      loss: pick(m, "training.loss", "loss") ?? null,
      wallClockSeconds: num(pick(m, "training.wallClockSeconds", "train_time_s", "training_seconds")),
    },
    source: sourceRef(modelFile),
  };
  log("model ←", modelFile.rel);
} else if (checkpointFile) {
  log("checkpoint found but no model metadata JSON; model section stays null (parameter counts are not guessed)");
}

// Simulator (+ optional replay)
const simulatorFile = locate("simulator");
if (simulatorFile) {
  const s = readJson(simulatorFile);
  const replayFile = locate("replay");
  let replay = null;
  if (replayFile) {
    const r = readJson(replayFile);
    replay = {
      scenarioId: String(pick(r, "scenarioId", "scenario_id") ?? "recorded"),
      frameTimes: (pick(r, "frameTimes", "times") ?? []).map(Number),
      timeUnit: String(pick(r, "timeUnit", "time_unit") ?? "steps"),
      frames: (pick(r, "frames") ?? []).map(maskRows),
      layers: pick(r, "layers") ?? null,
    };
  }
  next.simulator = {
    name: String(pick(s, "name", "simulator") ?? "unspecified simulator"),
    kind: ["forefire", "simplified"].includes(String(s.kind)) ? s.kind : /forefire/i.test(String(s.name ?? s.simulator)) ? "forefire" : "other",
    description: String(pick(s, "description") ?? ""),
    gridWidth: num(pick(s, "gridWidth", "grid_width", "nx")),
    gridHeight: num(pick(s, "gridHeight", "grid_height", "ny")),
    cellSizeMeters: num(pick(s, "cellSizeMeters", "cell_size_m", "resolution_m")),
    horizonSteps: num(pick(s, "horizonSteps", "horizon_steps", "steps")),
    sourceFiles: pick(s, "sourceFiles", "source_files") ?? [],
    replay,
    source: sourceRef(simulatorFile),
  };
  log("simulator ←", simulatorFile.rel, replay ? "(+ replay)" : "");
}

// Fuzzball workflow
const workflowFile = locate("fuzzballWorkflow");
if (workflowFile) {
  const w = readJson(workflowFile);
  const rawJobs = pick(w, "jobs", "workflow.jobs", "status.jobs") ?? [];
  const stageOf = (name) => (/sim/i.test(name) ? "simulation" : /data|shard|stage/i.test(name) ? "dataset" : /train/i.test(name) ? "training" : /eval|test|metric/i.test(name) ? "evaluation" : /infer|predict/i.test(name) ? "inference" : "other");
  const stateOf = (s) => {
    const v = String(s ?? "").toLowerCase();
    return v.includes("complet") || v.includes("finish") || v === "succeeded" ? "completed" : v.includes("fail") || v.includes("error") ? "failed" : v.includes("cancel") ? "cancelled" : v.includes("run") ? "running" : v.includes("pend") || v.includes("queue") ? "pending" : "unknown";
  };
  const jobs = (Array.isArray(rawJobs) ? rawJobs : Object.entries(rawJobs).map(([id, j]) => ({ id, ...j }))).map((j) => {
    const name = String(pick(j, "name", "id") ?? "job");
    return {
      id: String(pick(j, "id", "name")),
      name,
      stage: pick(j, "stage") ?? stageOf(name),
      start: pick(j, "start", "started_at", "start_time", "startTime") ?? null,
      end: pick(j, "end", "finished_at", "end_time", "endTime", "completed_at") ?? null,
      state: stateOf(pick(j, "state", "status", "phase")),
      dependsOn: pick(j, "dependsOn", "depends_on", "requires") ?? [],
      node: pick(j, "node", "host", "hostname", "placement.node", "nodeName") ?? null,
      resources: pick(j, "resources") ?? null,
      artifacts: pick(j, "artifacts", "outputs") ?? [],
    };
  });
  next.workflow = {
    workflowId: String(pick(w, "workflowId", "workflow_id", "id", "name") ?? path.basename(workflowFile.rel)),
    playback: "recorded",
    recordedAt: pick(w, "recordedAt", "recorded_at", "updated_at") ?? now,
    executionMode: ["sequential", "overlapping"].includes(w.executionMode) ? w.executionMode : "unknown",
    jobs,
    screenshots: pick(w, "screenshots") ?? null,
    source: sourceRef(workflowFile),
  };
  log("workflow ←", workflowFile.rel, `(${jobs.length} jobs)`);
}

// Benchmarks (JSON or metric,value,unit CSV)
const benchFile = locate("benchmarks");
if (benchFile) {
  let b;
  if (benchFile.rel.endsWith(".csv")) {
    b = {};
    const [header, ...rows] = readFileSync(benchFile.abs, "utf8").trim().split(/\r?\n/);
    const cols = header.split(",").map((c) => c.trim());
    for (const row of rows) {
      const cells = row.split(",");
      const rec = Object.fromEntries(cols.map((c, i) => [c, cells[i]?.trim()]));
      if (rec.metric) b[rec.metric] = num(rec.value);
    }
  } else b = readJson(benchFile);
  const measured = (v, unit) => (num(v) === null ? null : { value: num(v), unit });
  const pair = (a, b2) => (a && b2 ? true : false);
  const simS = measured(pick(b, "surrogateAcceleration.simulatorSecondsPerScenario.value", "simulator_seconds_per_scenario"), "s");
  const surS = measured(pick(b, "surrogateAcceleration.surrogateSecondsPerScenario.value", "surrogate_seconds_per_scenario", "inference_seconds_per_scenario"), "s");
  const one = measured(pick(b, "parallelThroughput.oneNodeScenariosPerSecond.value", "one_node_scenarios_per_second", "one_node_throughput"), "scenarios/s");
  const two = measured(pick(b, "parallelThroughput.twoNodeScenariosPerSecond.value", "two_node_scenarios_per_second", "two_node_throughput"), "scenarios/s");
  const seq = measured(pick(b, "workflowAcceleration.sequentialSeconds.value", "sequential_seconds"), "s");
  const ovl = measured(pick(b, "workflowAcceleration.overlappingSeconds.value", "overlapping_seconds"), "s");
  const train = measured(pick(b, "trainingCost.wallClockSeconds.value", "training_seconds", "train_time_s"), "s");
  next.benchmarks = {
    surrogateAcceleration: pair(simS, surS) ? { simulatorSecondsPerScenario: simS, surrogateSecondsPerScenario: surS, batchSize: num(pick(b, "surrogateAcceleration.batchSize", "batch_size")), hardware: pick(b, "surrogateAcceleration.hardware", "hardware") ?? null, includesDataLoading: pick(b, "surrogateAcceleration.includesDataLoading", "includes_data_loading") ?? null } : null,
    parallelThroughput: pair(one, two) ? { oneNodeScenariosPerSecond: one, twoNodeScenariosPerSecond: two } : null,
    workflowAcceleration: pair(seq, ovl) ? { sequentialSeconds: seq, overlappingSeconds: ovl } : null,
    trainingCost: train ? { wallClockSeconds: train, device: pick(b, "trainingCost.device", "device") ?? null } : null,
    latencySamplesMs: Array.isArray(pick(b, "latencySamplesMs", "latency_ms")) ? pick(b, "latencySamplesMs", "latency_ms").map(Number) : null,
    utilization: pick(b, "utilization") ?? null,
    workflowBreakdown: pick(b, "workflowBreakdown", "workflow_breakdown") ?? null,
    source: sourceRef(benchFile),
  };
  log("benchmarks ←", benchFile.rel);
}

// Ensemble (only if actually executed)
const ensembleFile = locate("ensemble");
if (ensembleFile) {
  const e = readJson(ensembleFile);
  const members = (e.members ?? []).map((m, k) => ({ id: String(m.id ?? k), label: String(m.label ?? `member ${k + 1}`), mask: maskRows(m.mask) })).filter((m) => m.mask);
  next.ensemble = { memberCount: members.length, description: String(e.description ?? ""), agreementMap: e.agreementMap ?? null, members, source: sourceRef(ensembleFile) };
  log("ensemble ←", ensembleFile.rel);
}

// Copy image assets (never move or modify originals)
const assetDir = path.join(projectRoot, "public/experiment-assets");
for (const rel of config.copyAssets ?? []) {
  const abs = path.join(repo, rel);
  if (existsSync(abs) && !dryRun) {
    mkdirSync(assetDir, { recursive: true });
    copyFileSync(abs, path.join(assetDir, path.basename(rel)));
    log("asset copied:", rel);
  }
}

const found = ["simulator", "dataset", "model", "fidelity", "workflow", "benchmarks", "ensemble"].filter((k) => next[k] !== null);
log(`repo: ${repo}`);
log(`sections populated: ${found.length ? found.join(", ") : "none"} (others remain awaiting)`);
if (dryRun) {
  console.log(JSON.stringify(next, null, 2).slice(0, 4000));
} else {
  if (existsSync(outPath)) writeFileSync(outPath.replace(/\.json$/, ".previous.json"), JSON.stringify(snapshot, null, 2));
  writeFileSync(outPath, JSON.stringify(next, null, 2));
  log("wrote", path.relative(projectRoot, outPath), "(previous snapshot kept as .previous.json)");
}
