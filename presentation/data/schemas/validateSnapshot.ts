/**
 * Lightweight schema validation. Invalid sections are dropped to null (shown as
 * "awaiting") and reported as issues; the deck never guesses or patches values.
 */
import type { PresentationSnapshot, SectionName } from "./presentationSchema";

export interface ValidationIssue {
  section: SectionName | "root" | "components";
  message: string;
}

type Guard = (value: unknown, issues: string[]) => void;

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const isNumberOrNull = (v: unknown) => v === null || v === undefined || (typeof v === "number" && Number.isFinite(v));

function requireKeys(value: Record<string, unknown>, keys: string[], issues: string[]) {
  for (const key of keys) if (!(key in value)) issues.push(`missing "${key}"`);
}

function requireSource(value: Record<string, unknown>, issues: string[]) {
  if (!isObject(value.source) || typeof value.source.path !== "string" || value.source.path.length === 0) {
    issues.push('missing "source.path" (every measured section must cite its artifact)');
  }
}

function checkMeasured(value: unknown, label: string, issues: string[]) {
  if (!isObject(value) || typeof value.value !== "number" || !Number.isFinite(value.value) || typeof value.unit !== "string") {
    issues.push(`${label} must be { value: number, unit: string }`);
  } else if (value.value < 0) {
    issues.push(`${label} must be non-negative`);
  }
}

function checkUnitInterval(value: unknown, label: string, issues: string[]) {
  if (value === null || value === undefined) return;
  if (typeof value !== "number" || value < 0 || value > 1) issues.push(`${label} must be in [0, 1] or null`);
}

function checkMetrics(value: unknown, label: string, issues: string[]) {
  if (!isObject(value)) {
    issues.push(`${label} must be an object`);
    return;
  }
  checkUnitInterval(value.iou, `${label}.iou`, issues);
  checkUnitInterval(value.precision, `${label}.precision`, issues);
  checkUnitInterval(value.recall, `${label}.recall`, issues);
  checkUnitInterval(value.f2, `${label}.f2`, issues);
  if (!isNumberOrNull(value.burnedAreaError)) issues.push(`${label}.burnedAreaError must be a number or null`);
}

function checkRowMask(value: unknown, label: string, issues: string[]) {
  if (value === null || value === undefined) return;
  if (!Array.isArray(value) || value.length === 0 || !value.every((r) => typeof r === "string" && /^[01]+$/.test(r))) {
    issues.push(`${label} must be an array of "0"/"1" row strings`);
    return;
  }
  const width = (value[0] as string).length;
  if (!value.every((r) => (r as string).length === width)) issues.push(`${label} rows must share one width`);
}

const sectionGuards: Record<SectionName, Guard> = {
  simulator(v, issues) {
    if (!isObject(v)) return void issues.push("must be an object");
    requireKeys(v, ["name", "kind", "description"], issues);
    requireSource(v, issues);
    if (isObject(v.replay)) {
      const replay = v.replay;
      if (!Array.isArray(replay.frames) || !Array.isArray(replay.frameTimes) || replay.frames.length !== replay.frameTimes.length) {
        issues.push("replay.frames and replay.frameTimes must be arrays of equal length");
      } else {
        (replay.frames as unknown[]).forEach((f, i) => checkRowMask(f, `replay.frames[${i}]`, issues));
      }
    }
  },
  dataset(v, issues) {
    if (!isObject(v)) return void issues.push("must be an object");
    requireKeys(v, ["splits", "inputChannels", "target"], issues);
    requireSource(v, issues);
    if (isObject(v.splits)) {
      for (const k of ["train", "validation", "test"]) if (!isNumberOrNull(v.splits[k])) issues.push(`splits.${k} must be a number or null`);
    }
    if (!Array.isArray(v.inputChannels)) issues.push("inputChannels must be an array");
  },
  model(v, issues) {
    if (!isObject(v)) return void issues.push("must be an object");
    requireKeys(v, ["modelType", "training"], issues);
    requireSource(v, issues);
    if (!isNumberOrNull(v.parameterCount)) issues.push("parameterCount must be a number or null");
  },
  fidelity(v, issues) {
    if (!isObject(v)) return void issues.push("must be an object");
    requireKeys(v, ["split", "aggregate", "examples"], issues);
    requireSource(v, issues);
    checkMetrics(v.aggregate, "aggregate", issues);
    if (!Array.isArray(v.examples)) return void issues.push("examples must be an array");
    v.examples.forEach((ex, i) => {
      if (!isObject(ex)) return issues.push(`examples[${i}] must be an object`);
      checkRowMask(ex.referenceMask, `examples[${i}].referenceMask`, issues);
      checkRowMask(ex.predictionMask, `examples[${i}].predictionMask`, issues);
      if (Array.isArray(ex.referenceMask) && Array.isArray(ex.predictionMask)) {
        if (ex.referenceMask.length !== ex.predictionMask.length || (ex.referenceMask[0] as string)?.length !== (ex.predictionMask[0] as string)?.length) {
          issues.push(`examples[${i}] reference and prediction must share resolution`);
        }
      }
      if (ex.metrics) checkMetrics(ex.metrics, `examples[${i}].metrics`, issues);
    });
  },
  workflow(v, issues) {
    if (!isObject(v)) return void issues.push("must be an object");
    requireKeys(v, ["workflowId", "jobs"], issues);
    requireSource(v, issues);
    if (v.playback !== "recorded") issues.push('playback must be "recorded" (live status is never synthesized)');
    if (!Array.isArray(v.jobs) || v.jobs.length === 0) return void issues.push("jobs must be a non-empty array");
    const ids = new Set((v.jobs as Array<Record<string, unknown>>).map((j) => j.id));
    (v.jobs as unknown[]).forEach((job, i) => {
      if (!isObject(job)) return issues.push(`jobs[${i}] must be an object`);
      if (typeof job.id !== "string") issues.push(`jobs[${i}].id must be a string`);
      if (job.start && Number.isNaN(Date.parse(String(job.start)))) issues.push(`jobs[${i}].start is not a timestamp`);
      if (job.end && Number.isNaN(Date.parse(String(job.end)))) issues.push(`jobs[${i}].end is not a timestamp`);
      if (job.start && job.end && Date.parse(String(job.end)) < Date.parse(String(job.start))) issues.push(`jobs[${i}] ends before it starts`);
      if (Array.isArray(job.dependsOn)) job.dependsOn.forEach((d) => { if (!ids.has(d)) issues.push(`jobs[${i}] depends on unknown job "${String(d)}"`); });
    });
  },
  benchmarks(v, issues) {
    if (!isObject(v)) return void issues.push("must be an object");
    requireSource(v, issues);
    const sa = v.surrogateAcceleration;
    if (isObject(sa)) {
      checkMeasured(sa.simulatorSecondsPerScenario, "surrogateAcceleration.simulatorSecondsPerScenario", issues);
      checkMeasured(sa.surrogateSecondsPerScenario, "surrogateAcceleration.surrogateSecondsPerScenario", issues);
    }
    const pt = v.parallelThroughput;
    if (isObject(pt)) {
      checkMeasured(pt.oneNodeScenariosPerSecond, "parallelThroughput.oneNodeScenariosPerSecond", issues);
      checkMeasured(pt.twoNodeScenariosPerSecond, "parallelThroughput.twoNodeScenariosPerSecond", issues);
    }
    const wa = v.workflowAcceleration;
    if (isObject(wa)) {
      checkMeasured(wa.sequentialSeconds, "workflowAcceleration.sequentialSeconds", issues);
      checkMeasured(wa.overlappingSeconds, "workflowAcceleration.overlappingSeconds", issues);
    }
    if (isObject(v.trainingCost)) checkMeasured(v.trainingCost.wallClockSeconds, "trainingCost.wallClockSeconds", issues);
    if (v.latencySamplesMs != null && (!Array.isArray(v.latencySamplesMs) || !v.latencySamplesMs.every((x) => typeof x === "number"))) {
      issues.push("latencySamplesMs must be an array of numbers");
    }
  },
  ensemble(v, issues) {
    if (!isObject(v)) return void issues.push("must be an object");
    requireKeys(v, ["memberCount", "members"], issues);
    requireSource(v, issues);
    if (Array.isArray(v.members)) (v.members as Array<Record<string, unknown>>).forEach((m, i) => checkRowMask(m?.mask, `members[${i}].mask`, issues));
  },
};

export const sectionNames: SectionName[] = ["simulator", "dataset", "model", "fidelity", "workflow", "benchmarks", "ensemble"];

/** Validates a raw snapshot; returns a cleaned copy plus every issue found. */
export function validateSnapshot(raw: unknown): { snapshot: PresentationSnapshot; issues: ValidationIssue[] } {
  const issues: ValidationIssue[] = [];
  const root = isObject(raw) ? raw : {};
  if (!isObject(raw)) issues.push({ section: "root", message: "snapshot is not an object; all sections treated as unavailable" });
  if (root.schemaVersion !== 1) issues.push({ section: "root", message: `unsupported schemaVersion ${String(root.schemaVersion)}` });

  const cleaned: PresentationSnapshot = {
    schemaVersion: 1,
    project: typeof root.project === "string" ? root.project : "Project Ember",
    generatedAt: typeof root.generatedAt === "string" ? root.generatedAt : null,
    isFixture: root.isFixture === true,
    components: Array.isArray(root.components) ? (root.components as PresentationSnapshot["components"]) : [],
    simulator: null,
    dataset: null,
    model: null,
    fidelity: null,
    workflow: null,
    benchmarks: null,
    ensemble: null,
  };

  for (const name of sectionNames) {
    const value = root[name];
    if (value === null || value === undefined) continue;
    const sectionIssues: string[] = [];
    sectionGuards[name](value, sectionIssues);
    if (sectionIssues.length > 0) {
      sectionIssues.forEach((message) => issues.push({ section: name, message }));
    } else {
      (cleaned as unknown as Record<string, unknown>)[name] = value;
    }
  }
  return { snapshot: cleaned, issues };
}
