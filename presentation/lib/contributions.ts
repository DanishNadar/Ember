/** Derives which contributions are demonstrated, strictly from snapshot evidence. */
import type { PresentationData } from "@/data/adapters/presentationData";

export interface Contribution {
  label: string;
  demonstrated: boolean;
  evidence: string;
}

export function deriveContributions(data: PresentationData): Contribution[] {
  const s = data.snapshot;
  const nodes = new Set((s.workflow?.jobs ?? []).map((j) => j.node).filter(Boolean));
  return [
    {
      label: "Reproducible simulation data generation",
      demonstrated: Boolean(s.simulator && s.dataset),
      evidence: s.dataset ? s.dataset.source.path : "needs simulator + data/manifest.json",
    },
    { label: "Neural approximation (U-Net surrogate)", demonstrated: Boolean(s.model), evidence: s.model ? s.model.source.path : "needs model metadata" },
    { label: "Measured surrogate fidelity", demonstrated: Boolean(s.fidelity), evidence: s.fidelity ? s.fidelity.source.path : "needs metrics/results.json" },
    { label: "HPC orchestration with Fuzzball", demonstrated: Boolean(s.workflow), evidence: s.workflow ? s.workflow.source.path : "needs Fuzzball logs" },
    { label: "Experiment defined as one Fuzzball workflow (Fuzzfile)", demonstrated: Boolean(s.workflowDefinition), evidence: s.workflowDefinition ? s.workflowDefinition.path : "needs your Fuzzfile" },
    { label: "Distributed execution across nodes", demonstrated: nodes.size >= 2, evidence: nodes.size >= 2 ? `${nodes.size} nodes in workflow log` : "needs logs showing ≥ 2 nodes" },
    {
      label: "Measured workflow / inference speedup",
      demonstrated: Boolean((data.workflowSpeedup && data.workflowSpeedup.ratio > 1) || (data.surrogateSpeedup && data.surrogateSpeedup.ratio > 1)),
      evidence: s.benchmarks ? s.benchmarks.source.path : "needs benchmark artifact",
    },
  ];
}

export const futureDirections = [
  "Better physical models",
  "Real environmental datasets",
  "Physics-informed learning",
  "Adaptive simulation requests",
  "Larger uncertainty ensembles",
  "Quantum-enhanced probability estimation (research direction, not implemented)",
];
