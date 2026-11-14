/**
 * Results adapter: turns a validated snapshot into what slides consume, including
 * derived ratios. Ratios are only computed when BOTH measured inputs exist, and each
 * comparison type (surrogate, parallel, workflow) stays separate — never multiplied
 * into one headline number.
 */
import type {
  ComponentStatus,
  EvidenceKind,
  PresentationSnapshot,
  SectionName,
} from "../schemas/presentationSchema";
import { validateSnapshot, type ValidationIssue } from "../schemas/validateSnapshot";

export interface DerivedComparison {
  ratio: number;
  numeratorLabel: string;
  denominatorLabel: string;
  description: string;
}

export interface PresentationData {
  snapshot: PresentationSnapshot;
  issues: ValidationIssue[];
  isFixture: boolean;
  surrogateSpeedup: DerivedComparison | null;
  parallelScaling: DerivedComparison | null;
  workflowSpeedup: DerivedComparison | null;
  evidenceFor: (section: SectionName) => EvidenceKind;
  componentStatus: (id: ComponentStatus["id"]) => ComponentStatus;
  availableSectionCount: number;
}

function safeRatio(numerator: number, denominator: number): number | null {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator <= 0 || numerator < 0) return null;
  return numerator / denominator;
}

export function buildPresentationData(raw: unknown): PresentationData {
  const { snapshot, issues } = validateSnapshot(raw);
  const bench = snapshot.benchmarks;

  let surrogateSpeedup: DerivedComparison | null = null;
  if (bench?.surrogateAcceleration) {
    const sa = bench.surrogateAcceleration;
    if (sa.simulatorSecondsPerScenario.unit === sa.surrogateSecondsPerScenario.unit) {
      const ratio = safeRatio(sa.simulatorSecondsPerScenario.value, sa.surrogateSecondsPerScenario.value);
      if (ratio !== null) {
        surrogateSpeedup = {
          ratio,
          numeratorLabel: "Simulator runtime / scenario",
          denominatorLabel: "Surrogate inference / scenario",
          description: "Surrogate acceleration: per-scenario simulator runtime divided by neural inference time. Excludes training cost.",
        };
      }
    } else {
      issues.push({ section: "benchmarks", message: "surrogate acceleration units differ; speedup not computed" });
    }
  }

  let parallelScaling: DerivedComparison | null = null;
  if (bench?.parallelThroughput) {
    const pt = bench.parallelThroughput;
    const ratio = safeRatio(pt.twoNodeScenariosPerSecond.value, pt.oneNodeScenariosPerSecond.value);
    if (ratio !== null) {
      parallelScaling = {
        ratio,
        numeratorLabel: "Two-node throughput",
        denominatorLabel: "One-node throughput",
        description: "Parallel throughput: scenarios per second on two nodes relative to one node.",
      };
    }
  }

  let workflowSpeedup: DerivedComparison | null = null;
  if (bench?.workflowAcceleration) {
    const wa = bench.workflowAcceleration;
    const ratio = safeRatio(wa.sequentialSeconds.value, wa.overlappingSeconds.value);
    if (ratio !== null) {
      workflowSpeedup = {
        ratio,
        numeratorLabel: "Sequential workflow",
        denominatorLabel: "Overlapping workflow",
        description: "Workflow acceleration: end-to-end sequential duration divided by overlapping producer-consumer duration.",
      };
    }
  }

  const evidenceFor = (section: SectionName): EvidenceKind => {
    const value = snapshot[section];
    if (value === null) return section === "ensemble" ? "proposed" : "unavailable";
    if (snapshot.isFixture) return "illustration";
    if (section === "simulator") return "simulatorDerived";
    return "verified";
  };

  const componentStatus = (id: ComponentStatus["id"]): ComponentStatus =>
    snapshot.components.find((c) => c.id === id) ?? { id, status: "unconfirmed", sourceFiles: [], note: null };

  const sections: SectionName[] = ["simulator", "dataset", "model", "fidelity", "workflow", "benchmarks", "ensemble"];

  return {
    snapshot,
    issues,
    isFixture: snapshot.isFixture,
    surrogateSpeedup,
    parallelScaling,
    workflowSpeedup,
    evidenceFor,
    componentStatus,
    availableSectionCount: sections.filter((s) => snapshot[s] !== null).length,
  };
}
