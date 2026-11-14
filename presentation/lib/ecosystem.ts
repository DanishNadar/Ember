/**
 * The hackathon technology stack and how Ember uses each layer.
 *
 * Two kinds of statements live here:
 *  1. Environment facts: what the organizers provided to every team, cited to the
 *     "SC26 Hackathon Introduction" deck (page numbers in `source`).
 *  2. Ember's use of each layer: its status comes from data/verified/ecosystemUsage.json
 *     (team-edited) and is upgraded to "verified" automatically when ingested Fuzzball
 *     logs prove it. The deck never upgrades a status on its own.
 */
import usageFile from "@/data/verified/ecosystemUsage.json";
import type { PresentationSnapshot } from "@/data/schemas/presentationSchema";

export const fuzzballGreen = "#11A66E";

export type UsageStatus = "verified" | "teamStated" | "environment" | "planned" | "unconfirmed";

export const usageStatusStyle: Record<UsageStatus, { label: string; color: string }> = {
  verified: { label: "Verified in workflow logs", color: "#35D6A0" },
  teamStated: { label: "Used by Ember", color: fuzzballGreen },
  environment: { label: "Hackathon environment", color: "#48D8FF" },
  planned: { label: "In Ember's workflow design", color: "#FFB547" },
  unconfirmed: { label: "To confirm", color: "#8A7266" },
};

export type StackLayerId =
  | "interfaces"
  | "ember"
  | "orchestrate"
  | "volumes"
  | "substrate"
  | "containers"
  | "os"
  | "hardware"
  | "storage";

export interface StackLayer {
  id: StackLayerId;
  vendor: "CIQ" | "NVIDIA" | "NVIDIA · Lenovo" | "VAST Data" | "Project Ember";
  title: string;
  environmentFact: string;
  source: string;
  emberUse: string;
  color: string;
  logo?: "fuzzball" | "ciq" | null;
}

export const stackLayers: StackLayer[] = [
  {
    id: "ember",
    vendor: "Project Ember",
    title: "Ember scientific-AI workflow",
    environmentFact: "Our simulation → dataset → U-Net surrogate → evaluation pipeline, packaged as one Fuzzball workflow.",
    source: "This project",
    emberUse: "Each stage is a containerized Fuzzball job with explicit dependencies, resources and artifacts.",
    color: "#FF6B35",
  },
  {
    id: "interfaces",
    vendor: "CIQ",
    title: "Fuzzball CLI · Web UI · SDK · MCP server",
    environmentFact: "Teams reach Fuzzball through a web interface, CLI, documentation and an MCP server.",
    source: "SC26 Hackathon Introduction, pp. 42–47",
    emberUse: "Validate, start, monitor and pull logs for the Ember workflow, and export the recorded run for this deck.",
    color: fuzzballGreen,
    logo: "fuzzball",
  },
  {
    id: "orchestrate",
    vendor: "CIQ",
    title: "Fuzzball Orchestrate (control plane)",
    environmentFact: "Manages data, container images and volumes. It schedules the workflow and provisions the resources it needs.",
    source: "SC26 Hackathon Introduction, p. 31",
    emberUse: "Turns our Fuzzfile into scheduled jobs: simulation shards, dataset build, training and evaluation, with dependency ordering.",
    color: fuzzballGreen,
    logo: "fuzzball",
  },
  {
    id: "volumes",
    vendor: "CIQ",
    title: "Fuzzball volumes · ingress / egress",
    environmentFact: "Each team has a dedicated volume provisioner, plus a shared provisioner with sample data and models.",
    source: "SC26 Hackathon Introduction, p. 34",
    emberUse: "A persistent volume carries simulation shards, the dataset manifest and checkpoints between jobs on different nodes. Egress exports metrics.",
    color: fuzzballGreen,
    logo: "fuzzball",
  },
  {
    id: "substrate",
    vendor: "CIQ",
    title: "Fuzzball Substrate (compute)",
    environmentFact: "Executes workflow jobs at scale on the compute nodes.",
    source: "SC26 Hackathon Introduction, pp. 31, 36",
    emberUse: "Runs Ember's containers on both GB10 nodes. GPU jobs request nvidia.com/gpu devices.",
    color: fuzzballGreen,
    logo: "fuzzball",
  },
  {
    id: "containers",
    vendor: "CIQ",
    title: "Container-first jobs (OCI / Apptainer)",
    environmentFact: "Fuzzball is container-first orchestration for HPC, AI/ML and data analytics on a single unified system.",
    source: "SC26 Hackathon Introduction, pp. 27, 30",
    emberUse: "Simulator and PyTorch surrogate run from pinned container images, so the experiment is reproducible.",
    color: "#C2AFA4",
    logo: "ciq",
  },
  {
    id: "os",
    vendor: "CIQ",
    title: "RLC Pro AI 9.8 (Rocky Linux from CIQ)",
    environmentFact: "Each team's two GB10 systems run RLC Pro AI 9.8: Enterprise Linux tuned for GPUs with the NVIDIA CUDA stack.",
    source: "SC26 Hackathon Introduction, pp. 18–19, 34",
    emberUse: "GPU drivers and CUDA come preinstalled on both nodes, so build time went into science instead of setup.",
    color: "#C2AFA4",
    logo: "ciq",
  },
  {
    id: "hardware",
    vendor: "NVIDIA · Lenovo",
    title: "2 × ThinkStation PGX · NVIDIA GB10 Grace Blackwell",
    environmentFact: "Every team builds and benchmarks on its own two-node GB10 cluster.",
    source: "SC26 Hackathon Introduction, pp. 2, 34",
    emberUse: "Node A generates simulations while Node B trains and evaluates the surrogate (placement verified only from logs).",
    color: "#76B900",
  },
  {
    id: "storage",
    vendor: "VAST Data",
    title: "VAST Data (hackathon partner)",
    environmentFact: "The judging criteria name VAST Data alongside NVIDIA and CIQ under Ecosystem Utility.",
    source: "SC26 Hackathon Introduction, pp. 1, 3, 5",
    emberUse: "Data layer for Ember's shared datasets and artifacts, if the team confirms it was used.",
    color: "#E5E7EB",
  },
];

type UsageEntry = { status: UsageStatus; detail?: string };
const usage = (usageFile as { layers: Record<string, UsageEntry> }).layers;

/** Effective status per layer: team file, upgraded only by real workflow evidence. */
export function layerStatus(id: StackLayerId, snapshot: PresentationSnapshot): { status: UsageStatus; detail: string | null } {
  const entry = usage[id] ?? { status: "unconfirmed" };
  const workflow = snapshot.isFixture ? null : snapshot.workflow;
  if (workflow && (id === "orchestrate" || id === "substrate")) {
    return { status: "verified", detail: `${workflow.jobs.length} jobs in ${workflow.workflowId}` };
  }
  if (workflow && id === "hardware") {
    const nodes = new Set(workflow.jobs.map((j) => j.node).filter(Boolean));
    if (nodes.size >= 2) return { status: "verified", detail: `${nodes.size} nodes recorded` };
  }
  return { status: entry.status, detail: entry.detail ?? null };
}

/** The four official evaluation criteria (SC26 Hackathon Introduction, pp. 3 and 5). */
export const judgingCriteria = [
  { id: "technical", title: "Technical Execution & Completeness", question: "Did you actually build a working, complex system?" },
  { id: "ecosystem", title: "Ecosystem Utility", question: "How effectively and meaningfully does the project leverage NVIDIA, CIQ, and VAST Data?" },
  { id: "impact", title: "Value & Impact", question: "Is the solution actually useful and valuable in the real world?" },
  { id: "innovation", title: "Innovation & Execution", question: "Did you push the boundaries of what's capable with the technology?" },
] as const;
