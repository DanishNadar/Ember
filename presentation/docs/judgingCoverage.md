# Judging Coverage Matrix

## What the official sources say
The CIQ announcement (Oct 7, 2026) describes the hackathon. Each team gets a multi-node cluster of two Lenovo ThinkStation PGX (NVIDIA GB10) systems orchestrated by CIQ Fuzzball. The challenge is to "build a real AI workload that makes full use of it", across four tracks: Multi-Node Training, Inference at Scale, **Scientific AI** (Ember's track), and Cluster & Scheduling. Teams train, serve and benchmark AI workloads.

**The announcement publishes no judging rubric, and none was found in this project. No rubric has been invented here.** The matrix below maps:
- (A) the documented challenge objectives, and
- (B) the twelve communication goals from the project brief.

Status key:
- ✅ covered with evidence
- 🟡 covered visually, evidence pending ingestion
- ⬜ not yet covered

Evidence status reflects the shipped snapshot (`data/verified/presentationSnapshot.json`), which is currently **empty** (no artifacts ingested). Re-check after running `npm run ingest`. The Explore → *Data & evidence* tab shows live status.

## (A) Documented challenge objectives

| Objective (source: CIQ press release) | Slide(s) | Supporting visual | Supporting artifact | Status |
|---|---|---|---|---|
| Real AI workload that makes full use of the multi-node cluster | 9, 10, 12 | Two-node scene, Gantt, parallel-throughput card | Fuzzball logs, benchmarks | 🟡 needs logs showing node placement, plus a two-node throughput measurement |
| Train AI workloads on the cluster | 8, 10 | Model card, training job bar | model metadata, Fuzzball logs | 🟡 |
| Serve / run inference | 12, 13 | Surrogate-acceleration card, ensemble explorer | benchmarks | 🟡 |
| Benchmark AI workloads | 12 | Benchmark dashboard (3 separate comparisons + training cost) | benchmarks CSV/JSON | 🟡 |
| Scientific AI track: distributed AI on a scientific workload | 2–8, 11 | Story arc, physics engine, triptych | simulator replay, results.json | 🟡 |
| Orchestration through Fuzzball | 5, 9, 10 | Architecture band, Fuzzball hub, Gantt | Fuzzball workflow definition + logs | 🟡 |

## (B) Communication goals from the brief

| # | Goal | Slide | Visual | Artifact | Evidence demonstrated | Missing evidence |
|---|---|---|---|---|---|---|
| 1 | The problem | 2, 3 | Condition-cycling landscape, scenario tree | — (illustrative) | Conceptual, clearly badged | — |
| 2 | Why it matters | 2 | Structures near the fire front | — | Narrative | — |
| 3 | Technical solution | 5 | Clickable pipeline | `snapshot.components` | Design shown | Component status file (`presentation/components.json`) |
| 4 | How AI is used | 7, 8 | Channel tensors, U-Net, model card | manifest, model metadata | Schematic | manifest.json, model metadata JSON |
| 5 | How the cluster is used | 9 | Planned vs Verified toggle | Fuzzball logs | Planned design only | Job→node placement from logs |
| 6 | What Fuzzball orchestrated | 10 | Recorded Gantt + contributions | Fuzzball logs | Planned DAG only | Workflow status JSON |
| 7 | What additional compute unlocked | 13 | Ensemble agreement explorer | ensemble outputs | Proposed extension (badged) | Recorded ensemble, if executed |
| 8 | Whether it works | 11 | Reference / prediction / error triptych | metrics/results.json | — | Held-out masks or images + metrics |
| 9 | What was measured | 11, 12 | Metric panel, benchmark cards | results.json, benchmarks | — | Both artifacts |
| 10 | Comparison vs baseline | 11, 12 | Baseline line, simulator vs surrogate bars | results.json `baselines`, benchmarks | — | Baseline metrics; simulator runtime |
| 11 | Reproducibility | 10, 14, Explore | Recorded workflow, SHA-256 per source | snapshot `source.sha256` | Ingest pipeline records hashes | Real artifacts |
| 12 | Limitations & future work | 11, 13, 14 | Captions, "not a calibrated probability", future list | — | Stated on slides | — |

## Not claimed anywhere in the deck
- Real-world forecast accuracy.
- Simultaneous use of both nodes, GPU saturation or distributed training, unless the logs show it.
- A combined speedup figure.
- Quantum computing in Ember.
