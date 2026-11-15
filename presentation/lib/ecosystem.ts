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
    title: "Ember: ForeFire → U-Net surrogate → DDP fine-tune",
    environmentFact: "ForeFire physics simulations become training data for a two-head U-Net surrogate that predicts burned area and fire arrival time. One model is then fine-tuned across both GPUs with PyTorch DistributedDataParallel over NCCL.",
    source: "This project",
    emberUse: "CPU physics and GPU training run side by side on each node; fresh labels are verified before they join training, and both GPU ranks finish with byte-identical weights.",
    color: "#FF6B35",
  },
  {
    id: "interfaces",
    vendor: "CIQ",
    title: "Fuzzball CLI · Web UI · SDK · MCP server",
    environmentFact: "Teams reach Fuzzball through a web interface, CLI, documentation and an MCP server.",
    source: "SC26 Hackathon Introduction, pp. 42–47",
    emberUse: "We used the Fuzzball CLI (v4.3.1) to package inputs, submit and monitor Ember's workflows, and retrieve hash-verified results.",
    color: fuzzballGreen,
    logo: "fuzzball",
  },
  {
    id: "orchestrate",
    vendor: "CIQ",
    title: "Fuzzball Orchestrate (control plane)",
    environmentFact: "Manages data, container images and volumes. It schedules the workflow and provisions the resources it needs.",
    source: "SC26 Hackathon Introduction, p. 31",
    emberUse: "Ran Ember's Fuzzfiles: image preparation, a one-GPU training run, then two training experiments in parallel on separate GB10 nodes, with every checkpoint retrieved and verified.",
    color: fuzzballGreen,
    logo: "fuzzball",
  },
  {
    id: "volumes",
    vendor: "CIQ",
    title: "Fuzzball volumes · ingress / egress",
    environmentFact: "Each team has a dedicated volume provisioner, plus a shared provisioner with sample data and models.",
    source: "SC26 Hackathon Introduction, p. 34",
    emberUse: "Our team scratch volume and object cache carried the input package in and checkpoints and metrics out. When the NFS mount failed, we switched to it without needing an admin.",
    color: fuzzballGreen,
    logo: "fuzzball",
  },
  {
    id: "substrate",
    vendor: "CIQ",
    title: "Fuzzball Substrate (compute)",
    environmentFact: "Executes workflow jobs at scale on the compute nodes.",
    source: "SC26 Hackathon Introduction, pp. 31, 36",
    emberUse: "Executed Ember's training containers on both GB10 nodes, one GPU each, with CUDA kernels doing the real training and evaluation.",
    color: fuzzballGreen,
    logo: "fuzzball",
  },
  {
    id: "containers",
    vendor: "CIQ",
    title: "Container-first jobs (OCI / Apptainer)",
    environmentFact: "Fuzzball is container-first orchestration for HPC, AI/ML and data analytics on a single unified system.",
    source: "SC26 Hackathon Introduction, pp. 27, 30",
    emberUse: "We built an ARM64 PyTorch + CUDA image for the GB10s; inputs and outputs are SHA-256 checked so every run is reproducible.",
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
    emberUse: "Both GB10 nodes trained Ember surrogates in parallel under Fuzzball, each on its own Blackwell GPU. CUDA and NCCL are the GPU stack behind training and the DDP fine-tune.",
    color: "#76B900",
  },
  {
    id: "storage",
    vendor: "VAST Data",
    title: "VAST Data (hackathon partner)",
    environmentFact: "The judging criteria name VAST Data alongside NVIDIA and CIQ under Ecosystem Utility.",
    source: "SC26 Hackathon Introduction, pp. 1, 3, 5",
    emberUse: "Hackathon data-platform partner, part of the ecosystem the event provided.",
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
