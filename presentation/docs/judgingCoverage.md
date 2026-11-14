# Judging Coverage Matrix

## Official criteria
Source: the organizers' *SC26 Hackathon Introduction* deck, pp. 3 and 5. Ember competes in **Track 3: Scientific AI**: "Apply distributed AI and accelerated computing to a scientific or research workload" (p. 4).

| # | Criterion | Official question |
|---|---|---|
| 01 | Technical Execution & Completeness | Did you actually build a working, complex system? |
| 02 | Ecosystem Utility | How effectively and meaningfully does the project leverage NVIDIA, CIQ, and VAST Data? |
| 03 | Value & Impact | Is the solution actually useful and valuable in the real world? |
| 04 | Innovation & Execution | Did you push the boundaries of what's capable with the technology? |

Scene **16 "Built for every criterion"** presents this mapping live. Its checkmarks are derived from the ingested snapshot, never typed in.

Legend:
- ✅ evidenced by ingested artifact
- 🟡 shown, evidence pending ingestion
- 💬 argument / design

The shipped snapshot is empty, so every artifact-backed row is 🟡 until `npm run ingest`.

### 01 · Technical Execution & Completeness
| Evidence point | Scene | Visual | Artifact | Status |
|---|---|---|---|---|
| Working pipeline: simulate → dataset → U-Net → evaluate | 5, 8, 9 | Clickable architecture, channel tensors, model card | manifest.json, model metadata | 🟡 |
| Held-out fidelity metrics, including failure cases | 13 | Reference / prediction / error triptych | metrics/results.json | 🟡 |
| Complete multi-stage run recorded by Fuzzball | 12 | Gantt reconstructed from job logs | Fuzzball workflow status JSON | 🟡 |
| Measured runtimes; training cost separate | 14 | Benchmark dashboard | benchmarks CSV/JSON | 🟡 |

### 02 · Ecosystem Utility (NVIDIA · CIQ · VAST Data)
| Layer | Provided by hackathon (source) | How Ember uses it | Scene | Default status |
|---|---|---|---|---|
| 2 × Lenovo ThinkStation PGX, NVIDIA GB10 | Each team's two-node cluster (pp. 2, 34) | Node A simulates, Node B trains/evaluates; GPU jobs request `nvidia.com/gpu` | 6, 10, 11 | Hackathon environment → verified when logs show ≥ 2 nodes |
| RLC Pro AI 9.8 (CIQ) | Runs on both GB10 systems (p. 34) | CUDA stack ready at first boot; no driver setup | 6 | Hackathon environment |
| Fuzzball Orchestrate (CIQ) | Control plane: data, images, volumes, scheduling (p. 31) | Schedules the Ember Fuzzfile's jobs with dependencies | 5, 6, 10, 11, 12 | Used by Ember (brief) → verified when logs are ingested |
| Fuzzball Substrate (CIQ) | Executes workflow jobs at scale (pp. 31, 36) | Runs Ember containers on both nodes | 6, 10 | Used by Ember (brief) → verified when logs are ingested |
| Fuzzball volumes | Dedicated per-team volume provisioner (p. 34) | Shards, manifest and checkpoints shared across jobs/nodes | 6, 10, 11 | Planned; team confirms |
| Fuzzball CLI / UI / SDK / MCP | Access methods (pp. 42–47) | Validate, start, monitor and export the run | 6, 11 | Planned; team confirms |
| Containers (OCI / Apptainer) | Container-first jobs (pp. 27, 30) | Pinned images for simulator and PyTorch | 6, 11 | Planned; team confirms |
| VAST Data | Named in the Ecosystem Utility criterion (pp. 3, 5) | Data layer, *only if confirmed* | 6, 16 | To confirm |

Status lives in `data/verified/ecosystemUsage.json` (or `presentation/ecosystemUsage.json` in your repo, picked up by `npm run ingest`).

### 03 · Value & Impact
| Point | Scene | Status |
|---|---|---|
| Faster what-if exploration of wildfire spread under uncertain conditions | 2, 3, 15 | 💬 |
| Ensemble agreement shows where outcomes are robust (not a calibrated probability) | 15 | 💬 proposed unless an ensemble is ingested |
| Explicit limits: fidelity to simulation ≠ forecast skill | 13, 17 | 💬 |

### 04 · Innovation & Execution
| Point | Scene | Evidence that turns it ✅ |
|---|---|---|
| Physics-trained neural surrogate replacing repeated simulator calls | 9, 13 | results.json |
| Producer–consumer overlap via Fuzzball `depends-on: RUNNING` | 11, 12, 14 | Measured sequential vs overlapping run (ratio > 1) |
| Two-node placement (simulate on A, learn on B) | 10, 12 | Logs showing ≥ 2 nodes |
| Every on-screen number traceable to an artifact with SHA-256 | All | Ingest pipeline |

## Never claimed by the deck
- Real-world forecast accuracy.
- Concurrency across nodes, GPU saturation or distributed training, unless the logs show it.
- A combined speedup figure.
- VAST Data usage without team confirmation.
- Quantum computing in Ember.
