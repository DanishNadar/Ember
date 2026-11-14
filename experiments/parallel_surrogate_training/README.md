# Parallel surrogate training experiment

**PGX users: start with [PGX_HANDOFF.md](PGX_HANDOFF.md).** It covers label conversion,
candidate preparation, frozen snapshots, per-node launch, resume, evaluation and inference.

## Entry points

| File | Purpose |
| --- | --- |
| `model.py` | Self-contained two-output U-Net; no dependency on sibling ML code |
| `export_sample.py` | Explicit aligned NPY label + prepared NPZ input conversion |
| `publish_shard.py` | Validate and atomically publish a completed producer shard |
| `check_data.py` | NumPy-only contract and leakage checks |
| `prepare_configs.py` | Create shared frozen snapshot and candidate A/B configs |
| `preflight.py` | CUDA runtime forward/backward compatibility probe |
| `run_pgx.sh` | Training job launcher inside the validated PGX environment |
| `train.py` | Training, validation, checkpoint continuation between rounds |
| `predict.py` | Unlabeled inference, held-out regional metrics and timing |
| `verify_handoff.py` | Tiny synthetic CPU integration verification |

Isolated implementation area for two independent GPU experiments fed by completed
CPU simulation batches. Existing ML, simulator and presentation files are untouched.
This is NOT DDP, elastic training, a simulator, or an implemented Fuzzball deployment.

## First run (repository root)

```powershell
python experiments/parallel_surrogate_training/smoke.py
```

Requires NumPy only. Creates explicitly synthetic fixtures under ignored `runs/`,
checks contracts/publication, and prints an optional tiny CPU training command.
It does not claim fire accuracy, actual training, CUDA or cluster performance.
Use the same Python that has NumPy installed. Training additionally requires a
working PyTorch build; keep the organizer's CUDA/ARM64 installation on the PGXs.

## What to implement here

1. Data team: exporter from actual ForeFire outputs to the contract below.
2. ML: run the tiny training fixture, then overfit a few REAL labeled samples.
3. Freeze validation/test and label the initial diverse training pool.
4. Run candidate A and B on separate PGXs with separate configs/output folders.
5. Publish more train-only shards; resume each model in a new training round.
6. Infrastructure: wrap these exact tested commands in the working Fuzzball setup.
7. Benchmark identical schedules on one node versus two nodes, including job startup,
   simulator generation, export, training and validation. Keep test evaluation final.

## Real sample contract

Copy `config.json` to customize. Paths inside configs resolve beside that config.
Default names match dataset v2.1's 19 channels, with `ignition` and `engine` explicitly
included. Arrays use CXY (east, north), NOT image row/column order. All arrays must
use the same grid. Geospatial correctness requires physical tests beyond shapes.

One NPZ per scenario:

- `x`: float32 `[19,320,320]`, unnormalized physical inputs.
- `arrival_time_seconds`: float32 `[320,320]`; reached cells within `[0,3600]`;
  unreached and invalid cells set to `-9999`.
- `valid_mask`: binary `[320,320]`; 0 means unknown/invalid, NOT nonburnable.
- `reached_mask`: binary `[320,320]`; reached by the horizon; subset of valid cells.
- `metadata_json`: scalar Unicode JSON string with `sample_id`, `simulation_id`,
  `scenario_family_id`, `region`, `engine_version`, `edge_hit: false`,
  `channel_names` (exact config order), `dataset_kind: "forefire"`,
  `horizon_seconds: 3600`, `cell_size_meters: 40`, `array_order: "CXY"`,
  `arrival_units: "seconds"`.

Exporter MUST explicitly convert old minutes/+inf formats, verify sentinel meaning,
retain actual simulator identity, align ignition and environmental fields, and use
meaningful family IDs. Do not fabricate labels or mark mock data as ForeFire.
OOD/site tests should use a separate evaluation setup, not be merged invisibly with
ordinary test metrics. Raw CSV scenario inputs alone cannot train this experiment.

## Safe batch publication

Write NPZs to `data/ready/batch_000/`, then atomically rename a temporary manifest
to `complete.json` LAST. Never overwrite a published shard. Manifest format:

```json
{"status":"complete","samples":[
  {"split":"train","file":"scenario001.npz","sha256":"ACTUAL_SHA256_OF_FILE"}
]}
```

Use `data_contract.digest(path)` to calculate hashes. At least one nonempty train,
val and test set is required. Same simulations/families cannot cross split boundaries.
The loader discovers published shards once per round; files do not enter mid-epoch.
It validates and hashes all splits but does not train/select on test labels.

## Training

Validate the real exported data first (NumPy only):

```bash
python experiments/parallel_surrogate_training/check_data.py --config experiments/parallel_surrogate_training/config.json
```

```bash
python experiments/parallel_surrogate_training/train.py --config experiments/parallel_surrogate_training/config.json --output experiments/parallel_surrogate_training/runs/A_round1 --device cuda
python experiments/parallel_surrogate_training/train.py --config experiments/parallel_surrogate_training/config.json --output experiments/parallel_surrogate_training/runs/A_round2 --resume experiments/parallel_surrogate_training/runs/A_round1/last.pt --device cuda
```

Publish extra TRAIN shards before round 2. Validation/test content must stay identical;
prior training samples must remain intact. Normalization and optimizer state are
preserved. New hyperparameters require a separate experiment, not resume. Each round
selects its own best checkpoint; compare best checkpoints across rounds using the
same validation criterion. Only load trusted team checkpoints.

For candidate B, copy the config and alter ONE meaningful choice (e.g. arrival loss
weight); run on the other PGX with its own output directories. Both should use the
same frozen snapshot for comparison. Use `--evaluate-test` only on the final selected
experiment. Training defaults to CUDA and fails if unavailable instead of silently
falling back. `--device cpu` is for debugging.

## What the outputs establish

- `snapshot.json`: exact sample paths, identities and hashes for reproducibility.
- `config.json`, `best.pt`, `last.pt`: configuration, model and optimizer state.
- `events.jsonl`: real host timestamps, epoch wall time, throughput, losses, metrics.
- Validation: micro/macro IoU at 10/20/30/60 minutes, new-spread IoU, persistence
  comparisons, empty-mask counts and arrival MAE on reached cells. Empty-union IoU
  is defined as 1, so inspect the empty counts. Arrival MAE alone misses classification
  failures; always report it with burn agreement. `predict.py --split val/test` adds
  per-region metrics and recall without fitting test data.

GPU peak PyTorch allocation is NOT GPU utilization or total memory consumption.
Collect CPU/GPU activity, memory contention, node placement, simulator timings and
Fuzzball job logs separately. Throughput is training/evaluation pipeline time, NOT
standalone inference latency. No speedup is claimed by the existence of these files.

## Current deliberate limits

No automatic simulator queue, raw-engine extraction, Fuzzball API, dynamic resource
allocation, mixed precision tuning, plotting or DDP. The explicit label converter
requires already aligned inputs/arrival arrays; the data team must verify these.
Hash checking per sample is conservative and adds I/O; optimize only after validating
the end-to-end path. One GPU process per node; adjust CPU workers in the simulator
outside this folder after measuring contention. Checkpoints capture torch RNG state;
exact replay across different hardware/software is not guaranteed.
