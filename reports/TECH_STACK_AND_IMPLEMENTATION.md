# Project Ember — Technology Stack and Implementation Plan

**Document status:** Proposed architecture and integration plan; not a validated benchmark  
**Date:** 2026-11-14  
**Physics engine decision:** **ForeFire only** for this hackathon  
**Primary objective:** Reproduce numerical ForeFire wildfire-spread outputs with a fast neural surrogate, and measure whether a two-node simulation/training workflow improves time to a useful model.

> **Scientific scope:** Ember emulates a physics-based simulator. Agreement with ForeFire does **not** establish reliable real-world wildfire forecasting. All claimed accuracy and speedups must come from executed, reproducible experiments.

## 1. Current repository state and decisions

The [`main` README](../README.md) documents reference-artifact extraction, not a completed end-to-end native ForeFire run. In particular, the repository's `*.ref` KML/NetCDF files are **reference fixtures**, not new simulation results. The existing [`scripts/run_forefire.py`](../scripts/run_forefire.py) is the appropriate starting point for a real execution, with failure and runtime recorded honestly.

Two open **draft** pull requests influence, but do not yet establish, this design:

- [PR #1 — direct arrival-time surrogate](https://github.com/DanishNadar/Ember/pull/1) proposes a two-head U-Net and a strict per-simulation NPZ loader. Its author explicitly notes that Python tests, ForeFire execution, and GPU training were **not run** for that draft.
- [PR #2 — resource-handoff experiment](https://github.com/DanishNadar/Ember/pull/2) proposes an isolated local orchestration smoke test and Fuzzball workflow template. It describes **independent** jobs and a completion-based handoff, **not** a verified streaming dataset pipeline or elastic distributed training. Fuzzball execution on the actual cluster is still unverified.

**Architecture decisions:**

1. Use **ForeFire**, initially on the bundled **Aullène** landscape. Do not introduce ELMFIRE or another physics engine into the main pipeline.
2. Train a **two-head direct-prediction U-Net** as proposed by PR #1: burn-within-horizon classification plus conditional arrival-time regression. This is a proposed model, not an established result.
3. Use the supplied **two NVIDIA GB10 machines**, **Fuzzball**, and the team-accessible **shared storage provisioner**. Access to Fuzzball is already set up; job, volume, and GPU behavior still requires end-to-end testing.
4. Prioritize one complete, simulator-generated, valid NPZ sample and successful ML ingestion before large dataset generation, new geographic regions, or presentation features.

## 2. Required software and services

| Layer | Software / service | Purpose | Deployment action |
|---|---|---|---|
| Physics | [ForeFire](https://github.com/forefireAPI/forefire) | Execute wildfire scenarios; export numerical arrival times | Install/test in Linux ARM64 simulation environment |
| Primary landscape | Bundled Aullène `data.nc`, `fuels.csv`, scenario `.ff` files | Elevation, mapped fuel properties, starting scenario | Ensure Git LFS payloads are downloaded; inspect metadata |
| Numerical processing | Python, NumPy, SciPy, Xarray, NetCDF4 | Read outputs, validate units and arrays, generate NPZ | Reuse compatible pinned dependencies in [`requirements.txt`](../requirements.txt) |
| Geospatial processing | Rasterio, PyProj | Coordinate transforms, cropping, resampling, grid alignment | Install where needed on Linux workers; do not resample fuel classes with bilinear interpolation |
| ML | PyTorch + CUDA | Train/evaluate the two-head U-Net | Select an **ARM64/GB10-compatible GPU image** and verify CUDA availability |
| Orchestration | CIQ Fuzzball | Launch/monitor containerized simulation and training jobs | Use already configured Fuzzball environment; validate target workflow syntax |
| Storage | Team's Fuzzball provisioned shared volume (VAST-backed where configured) | Exchange validated NPZ batches, logs, model checkpoints | Test read/write access and simultaneous mounting on both nodes |
| Packaging | OCI-compatible containers | Isolate native simulation and GPU training dependencies | Build/publish `ember-sim` and `ember-train` images for `linux/arm64` |
| Monitoring | Python monotonic timers, UTC event logs, psutil, CUDA events, Fuzzball logs | Establish credible speed, memory, GPU and workflow metrics | Record reproducible per-run metadata |
| Visualization | Streamlit + Plotly (proposed) | Compare simulator, surrogate and error maps; show measured charts | Implement only after first real outputs are available |
| Collaboration | Git/GitHub | Source, PR review, traceability | Keep changes isolated by workstream |

**Not needed for the MVP:** Kubernetes, Kafka, Slurm, extra cloud GPU services, a second physics engine, or distributed-data-parallel U-Net training.

## 3. End-to-end architecture

```text
Aullène landscape + scenario settings
                 |
                 v
      Node 1: ForeFire native run
                 |
          numeric arrival grid
                 |
    validate geospatial/time metadata
                 |
       per-simulation NPZ export
                 |
       publish completed sample
                 v
      shared Fuzzball storage
                 |
                 v
      Node 2: PyTorch U-Net
                 |
          checkpoint + metrics
                 |
                 v
       evaluation + visual demo

Fuzzball schedules the jobs and captures their placement, logs, and runtimes.
```

**Desired pipeline:** simulation generation continues while training consumes **earlier completed** simulations. This is a planned experiment, not a feature proven by the current draft PRs. The separate PR #2 resource-handoff experiment should remain distinct unless the infrastructure owner chooses to integrate it.

### Node 1 — ForeFire simulation worker

- Start from `forefire/tests/runff/real_case.ff` and the corresponding landscape/fuel files.
- Confirm a **native** execution produces a new numerical arrival-time NetCDF, rather than reading `ForeFire.0.nc.ref`.
- Generate parameterized scenario files with run-specific identifiers, input values, random seeds where relevant, and output locations.
- Inspect and transform each result into the final ML grid **without changing its physical meaning**.
- Write one complete NPZ file per independent simulation; publish only after validating it.
- Log wall-clock runtime, processor and memory metrics, start/end UTC timestamps, and any failures.

### Node 2 — PyTorch training worker

- Check shared storage for **completed** training samples.
- Validate the exact NPZ schema and expected channels before use.
- Train the proposed two-head U-Net and periodically evaluate using a **predefined, fixed, family-disjoint validation set**.
- Save model checkpoints, loss/accuracy metrics, input manifest version, and batch provenance.
- Record CUDA inference measurements using GPU synchronization/CUDA events, plus GPU resource information if available.

**Storage contract:** publish to a temporary filename and atomically rename it to a final `.npz` file on the same filesystem. A separate completion marker/manifest distinguishes finished production from a stalled producer. Validate simultaneous visibility across nodes first; not every storage setup guarantees the same semantics.

## 4. ForeFire scenario specification

Initial **proposed** values, pending native validation:

| Parameter | Proposed handling |
|---|---|
| Wind speed and direction | Vary across runs; encode physical units and convention |
| Wind shifts | Include shift magnitude **and the actual time of change**; defer dynamic shifts until constant-wind runs pass |
| Dead fuel moisture | Vary using correctly interpreted ForeFire fuel parameters; preserve source units |
| Ignition | One or more coordinates/perimeters, explicitly transformed to the landscape coordinate reference |
| Fuel map | Begin with Aullène's compatible map/`fuels.csv` pairs; preserve categorical meaning |
| Elevation/slope | Use aligned terrain grids; derive slope using metric horizontal spacing if required |
| Spatial grid | Target 320 × 320 cells, nominal 40 m each, covering 12.8 km × 12.8 km |
| Forecast horizon | Target 3,600 seconds; the bundled example's duration may differ |

The **320 × 320 export grid is not automatically the simulator's internal numerical resolution**. Verify geographic bounds, X/Y orientation, cell-center convention, coordinate reference system, and time origin. Changes in spatial resolution must be benchmarked, not asserted to produce specific runtime scaling.

**Fuel portability:** ForeFire's Rothermel implementation accepts fuel parameters; this does **not** prove that every Scott & Burgan/LANDFIRE category or dynamic curing behavior is correctly implemented. A U.S. landscape is an **optional extension** requiring fuel-code mapping, consistent physical parameterization, and an actual native test. Do not claim validated state-by-state U.S. predictions.

## 5. ML sample contract and data quality

Align exporter code to the **proposed PR #1 contract**, not the older `x`/`y` temporal-pair convention, unless the ML and simulation owners jointly change the specification.

| NPZ field | Expected value |
|---|---|
| `x` | `float32 [C, H, W]`, with approved ordered feature channels |
| `arrival_time_seconds` | `float32 [H, W]`, one full ForeFire simulation's output |
| `channel_names` | Ordered names exactly matching the `C` input channels |
| `simulation_id` | Unique ID for a native ForeFire run |
| `scenario_family_id` | Group ID for related conditions/landscape/ignitions used in split auditing |
| `dataset_kind` | `"forefire"` |
| `horizon_seconds` | Actual prediction horizon, not a hard-coded guess |
| `cell_size_meters` | Actual projected grid cell spacing |

PR #1 proposes `-9999` as the **exported** sentinel for unreached cells; it is **not a claim about ForeFire's native sentinel**. The exporter must identify the native valid/invalid convention first and then translate it consistently. Invalid cells should be excluded from arrival-time loss and error reporting, and mask derivation must not interpret `-9999` as an early arrival.

If two runs have different future wind schedules or moisture but the same `x`, the mapping is ambiguous. Encode every varied generating input, including shift time and post-shift wind vector. Keep categorical fuel identifiers stable across all samples (e.g., agreed one-hot channels).

**Independent evaluation:** all related timesteps, crops and perturbations of a scenario family must remain in the same train/validation/test split. For landscape generalization claims, reserve geographically distinct landscapes for testing. A model trained and evaluated solely on different Aullène scenarios cannot establish U.S. generalization.

### Data validation gate

Before the ML team accepts a sample:

1. Native simulator execution is documented, with a fresh result path and runtime log.
2. `x` and `arrival_time_seconds` have the declared shapes/dtypes, consistent aligned coordinates, and finite/valid values as applicable.
3. Arrival-time units and ignition/start-time origin are verified; unreached cells have an explicit convention.
4. The sample contains the actual scenario metadata, including future wind schedule when used.
5. `simulation_id` and `scenario_family_id` are present and stable.
6. The draft PR #1 loader consumes the file successfully in a local smoke test.

## 6. Fuzzball deployment and storage plan

The event provides two GB10 systems and a dedicated volume provisioner, but **actual** container execution, volume mounts, GPU visibility, and placement still need verification.

1. Build/publish a Linux ARM64 **simulation container** with ForeFire and numerical I/O dependencies.
2. Build/publish a validated Linux ARM64 **training container** with CUDA-enabled PyTorch.
3. Test both jobs separately; print architecture and record image tags/versions.
4. Mount a shared persistent volume in each and perform a small cross-node write/read test.
5. Confirm PyTorch reports CUDA support **inside the Fuzzball training job**.
6. Submit concurrent jobs; verify they actually landed on distinct hosts, using Fuzzball placement logs.
7. Implement a batch consumer that can wait for the **first completed** file, continue training as more arrive, and terminate on a verified producer completion signal.
8. Only then run one-node and two-node comparisons.

The orchestration draft in [PR #2](https://github.com/DanishNadar/Ember/pull/2) is a **resource-handoff experiment**, not the final streaming pipeline. In particular, its `FINISHED` dependency and mocked smoke test must not be represented as proof of success-gated execution on the live cluster. Retain it as an independent experiment unless owners explicitly integrate it.

**Security and reproducibility:** use team-scoped Fuzzball secrets for registry credentials; do not commit tokens, private service credentials, or large generated artifacts to Git. Log code commit, container digest, simulator version, model config, input-manifest checksum, hardware allocation and run seeds.

## 7. Evaluation protocol

### A. Scientific agreement with the simulator

- Burned-area IoU at **10, 20, 30 and 60 minutes**, derived from the same horizon-relative arrival-time grid.
- Arrival-time MAE **on reached and valid cells**, with the evaluated mask stated.
- Fire-front displacement where feasible.
- Results stratified by wind conditions, ignition location, moisture and scenario family to expose failure modes.

These are **ForeFire agreement metrics**, not real-wildfire forecasting accuracy.

### B. Surrogate acceleration

Measure **ForeFire elapsed seconds per scenario** against **trained U-Net inference latency** at clearly stated batch sizes and precision, and report prediction accuracy alongside speed. Include data preprocessing and model load/warmup choices explicitly; do not conflate batch throughput with single-query latency.

### C. Workflow acceleration

Benchmark the same scenario schedule, dataset split, model/hyperparameters and evaluation rule under:

1. **Sequential, one node:** generate first, then train.
2. **Concurrent, one node:** reasonable CPU simulation + GPU training overlap.
3. **Concurrent, two nodes:** separate jobs on two GB10 machines.

Report total wall time, **time to a fixed validation threshold**, generated scenarios/sec, training throughput, CPU/GPU utilization, peak memory, storage time and actual Fuzzball job overlap. Repeat runs where practical. The **concurrent one-node** baseline is necessary to isolate benefit from the second computer rather than merely from overlap.

### D. Break-even

A simple time-based estimate is:

`N_break_even = (T_data_generation + T_training) / (T_ForeFire_per_query - T_U-Net_per_query)`

Use this only when the denominator is positive and the accuracy requirement is met. Also report resource-hours or financial cost where possible; using two nodes can lower elapsed time without lowering total compute consumption. Large ensemble workloads are a hypothesis to test, not a proven result.

## 8. Implementation milestones, owners, and acceptance criteria

| Order | Deliverable | Proposed owner | Pass condition |
|---|---|---|---|
| 1 | ARM64 native ForeFire verification | Simulation: Vijay + Sashank | Fresh numerical arrival-time output, correct units/extent, runtime log |
| 2 | Single real NPZ sample | Simulation + ML | PR #1 loader reads a valid, complete native-run sample |
| 3 | Scenario generator + split manifest | Simulation + ML | Repeatable independent runs; family-disjoint splits |
| 4 | U-Net baseline training | ML | Training executes on GB10 GPU; held-out metrics and checkpoint saved |
| 5 | Shared storage + two job images | Infrastructure | Both jobs mount/read/write volume; correct GPU/host placement |
| 6 | Incremental pipeline | Infrastructure + simulation + ML | Training begins before all generation finishes, with real timestamps |
| 7 | Fair performance comparison | Benchmarking + all workstreams | A/B/C configurations and confidence/limitations reported |
| 8 | Visual demonstration | Visualization | Real simulator/predicted/error maps and measured performance charts |

**Current hard blockers:** no verified native output on the target cluster has been presented in the repository's documented main workflow; exporter and draft ML NPZ contracts disagree; independent training data are insufficient; a cluster-verified streaming pipeline is not yet established.

**MVP completion criterion:** `native ForeFire run → numeric arrival-time extraction → validated full-simulation NPZ → U-Net loads/trains → shared-volume Fuzzball execution → measured accuracy and runtime`. Do not expand to another landscape before this sequence works.

## 9. Deferred features and exclusions

**Defer until MVP is verified:** LANDFIRE U.S. landscapes, active-learning selection of runs, inverse estimation of ignition/wind, advanced dynamic weather schedules, large-scale ensembles and elaborate frontend animations.

**Explicitly out of scope:** operational wildfire warnings, claims of real-world prediction accuracy, a second physics engine, and automatically claiming two-node speedups without measured one-node concurrent baselines.

## 10. References

- [Ember repository / README](https://github.com/DanishNadar/Ember)
- [PR #1 — experimental direct-arrival U-Net and NPZ contract](https://github.com/DanishNadar/Ember/pull/1)
- [PR #2 — experimental resource handoff](https://github.com/DanishNadar/Ember/pull/2)
- [ForeFire official repository](https://github.com/forefireAPI/forefire)
- [ForeFire documentation](https://forefire.readthedocs.io/)
- [Fuzzball documentation](https://docs.ciq.com/fuzzball)
- [PyTorch](https://pytorch.org/)
- [LANDFIRE](https://www.landfire.gov/)

---

**Decision summary:** Commit to **ForeFire + Python scientific I/O + PyTorch U-Net + Fuzzball + shared storage**. Make simulation correctness and the NPZ contract the first integration gate. Add data diversity and performance claims only after the complete pipeline is demonstrably operational.
