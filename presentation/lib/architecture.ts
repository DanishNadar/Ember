/**
 * Planned architecture of Project Ember, described from the project brief.
 * Implementation status is NOT asserted here: it comes from snapshot.components.
 */
import type { ComponentStatus } from "@/data/schemas/presentationSchema";

export interface ArchitectureComponent {
  id: ComponentStatus["id"];
  order: number;
  title: string;
  shortTitle: string;
  color: string;
  role: string;
  inputs: string[];
  outputs: string[];
  compute: string;
  dataContract: string;
}

export const architectureComponents: ArchitectureComponent[] = [
  {
    id: "simulation",
    order: 1,
    title: "Physics simulation",
    shortTitle: "Simulate",
    color: "#FF6B35",
    role: "Runs the wildfire simulator over sampled environmental conditions to produce reference fire progressions.",
    inputs: ["Ignition / initial burned area", "Wind speed and direction", "Fuel and moisture maps", "Terrain and slope"],
    outputs: ["Burned-area masks over simulation time", "Per-scenario configuration record"],
    compute: "CPU-bound, embarrassingly parallel across scenarios.",
    dataContract: "scenario config → time series of burned-extent masks",
  },
  {
    id: "dataset",
    order: 2,
    title: "Generated training data",
    shortTitle: "Dataset",
    color: "#FFB547",
    role: "Converts completed simulations into aligned input-channel tensors and future-mask targets, split by scenario.",
    inputs: ["Simulator outputs", "Environmental layers"],
    outputs: ["Training / validation / test shards", "data/manifest.json"],
    compute: "I/O and CPU; light preprocessing.",
    dataContract: "(C × H × W inputs, 1 × H × W target) pairs + manifest",
  },
  {
    id: "surrogate",
    order: 3,
    title: "Neural surrogate",
    shortTitle: "Surrogate",
    color: "#48D8FF",
    role: "A lightweight U-Net-style network that learns to map current state and conditions to the future burned extent.",
    inputs: ["Input-channel tensors"],
    outputs: ["Predicted burned-area probability / mask", "models/best.pt checkpoint"],
    compute: "GPU training; fast batched GPU inference.",
    dataContract: "C × H × W → 1 × H × W",
  },
  {
    id: "evaluation",
    order: 4,
    title: "Model evaluation",
    shortTitle: "Evaluate",
    color: "#35D6A0",
    role: "Scores surrogate predictions against held-out simulator outputs and records runtime benchmarks.",
    inputs: ["Held-out test scenarios", "Checkpoint"],
    outputs: ["metrics/results.json (IoU, precision, recall, F2, area error)", "outputs/comparison.png"],
    compute: "GPU inference plus CPU metric computation.",
    dataContract: "predictions + references → metrics JSON",
  },
  {
    id: "orchestration",
    order: 5,
    title: "Fuzzball orchestration",
    shortTitle: "Fuzzball",
    color: "#11A66E",
    role: "Runs Ember as one Fuzzball workflow. Orchestrate (control plane) schedules jobs and provisions resources. Substrate executes them on both GB10 nodes. Volumes carry shards and checkpoints between stages.",
    inputs: ["Fuzzfile (v4 workflow definition)", "Container images", "Resource requests (cores, memory, nvidia.com/gpu)"],
    outputs: ["Scheduled jobs on the two-node cluster", "Job logs, states and placement", "Artifacts on the persistent volume"],
    compute: "Control plane plus compute substrate. It orchestrates the work and does not train the model.",
    dataContract: "Fuzzfile → jobs (task-array, depends-on, devices) → recorded run",
  },
  {
    id: "exploration",
    order: 6,
    title: "Distributed scenario exploration",
    shortTitle: "Explore",
    color: "#48D8FF",
    role: "Uses the trained surrogate to evaluate many condition sets quickly, across available nodes.",
    inputs: ["Checkpoint", "Scenario sweep definition"],
    outputs: ["Predicted footprints per scenario", "Ensemble agreement summaries"],
    compute: "GPU inference, parallel across scenarios and nodes.",
    dataContract: "scenario batch → predicted masks",
  },
];

export const statusStyles: Record<ComponentStatus["status"], { label: string; color: string }> = {
  implemented: { label: "Implemented", color: "#35D6A0" },
  partial: { label: "Partially implemented", color: "#FFB547" },
  proposed: { label: "Proposed", color: "#A78BFA" },
  unconfirmed: { label: "Status unconfirmed", color: "#5B6678" },
};
