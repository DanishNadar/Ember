# PGX handoff: parallel simulation and surrogate experiments

## Scope and ownership

This folder is self-contained (including `model.py`). It runs one GPU training
experiment per job. A and B are independent candidates, NOT distributed training.
CPU ForeFire generation runs in separate team-owned jobs. This folder never
changes ForeFire, installs drivers, calls cloud APIs, or submits Fuzzball jobs.

Data team supplies physically verified inputs/labels; ML owns training/evaluation;
infrastructure owns actual image, mounts, CPU quotas, GPU allocation and node placement.
The launcher can be used as a Fuzzball job command after the infrastructure team
validates those details. Do not substitute made-up registry or volume names.

## 1. Environment check inside the PGX container

Use Python 3.12 and the organizer's working ARM64/CUDA PyTorch installation.
Do NOT replace it with the laptop CPU wheel. Do not run a blanket dependency upgrade.

```bash
python3 experiments/parallel_surrogate_training/preflight.py
```

This checks a small forward/backward pass on CUDA and prints runtime identity.
Failure is a real deployment blocker. This does not establish utilization or accuracy.

## 2. Export real labels

Prepared input NPZ must contain `x`, `valid_mask`, and scalar Unicode
`metadata_json` with the metadata specified in README, plus actual `simulation_id`,
`scenario_family_id`, and `edge_hit`. Inputs are physical values, not pre-normalized.
Use dataset v2.1's `input_tensor` output with exact channel names. Preserve sample ID.

Extract arrival output as an aligned XY NPY. Verify simulator sentinel, seconds versus
minutes, origin, initial ignition values, grid, horizon, fuel/wind conventions and
validity against a controlled real run. The adapter rejects unknown negative values.
It does not guess that all negatives mean ignition, nor that every infinity is valid.

```bash
python3 experiments/parallel_surrogate_training/export_sample.py \
  --config experiments/parallel_surrogate_training/config.json \
  --inputs /shared/prepared/scenario001_inputs.npz \
  --arrival /shared/raw/scenario001_arrival.npy \
  --source-units seconds --source-unreached inf --split train \
  --output /shared/ember/ready/batch_000/scenario001.npz
python3 experiments/parallel_surrogate_training/publish_shard.py \
  --config experiments/parallel_surrogate_training/config.json \
  --shard /shared/ember/ready/batch_000
```

These shared paths are examples; use your verified mounted paths. Each producer owns
a distinct shard. Publish after all writes finish; never append to published shards.
Reject known-invalid edge-hit cases, recording reasons in the producer's audit log.
Valid no-spread cases must not be removed just to improve accuracy. Assign actual
related scenario families consistently across splits. Set `engine_version` to a
concrete simulator build and patch identity. Engine ID is already input channel 18.

## 3. Prepare candidates ONCE on shared storage

The ready root needs nonempty train/val/test samples (they can reside in different
shards). Keep Arizona/OOD in a separate evaluation experiment; don't train on it.

```bash
python3 experiments/parallel_surrogate_training/prepare_configs.py \
  --data /shared/ember/ready --output /shared/ember/experiment_001
```

This validates data and freezes an explicit snapshot shared by both candidates.
Candidate A uses arrival weight 1; B uses 2. Everything else starts identical.
These are starting configurations, NOT tuned settings. Compare candidates by the
SAME physical metric (e.g. macro IoU and arrival MAE on the same validation set),
NOT raw weighted loss: the candidates have different loss weights.

## 4. Launch one GPU job on each PGX

Node 1 GPU:

```bash
bash experiments/parallel_surrogate_training/run_pgx.sh \
  /shared/ember/experiment_001/candidate_A.json \
  /shared/ember/experiment_001/A_round1 \
  /shared/ember/experiment_001/snapshot.json
```

Node 2 GPU: same command with candidate_B.json and B_round1.
Infrastructure must verify actual different-node placement in Fuzzball logs.
Concurrently run disjoint CPU simulation shards, initially with conservative worker
counts. Reserve CPU time and RAM for the GPU trainers/loaders. Increase workers only
if valid-label throughput rises without harming training throughput.

New training data enters the NEXT round. Generate a new shared snapshot/config
directory, preserving validation/test and old train records; pass prior `last.pt`
as the fourth launcher argument. The normalizer stays frozen from round 1.
Don't modify channel definitions, physics conventions or hyperparameters on resume.

## 5. Validate/select, then evaluate final test ONCE

```bash
python3 experiments/parallel_surrogate_training/predict.py \
  --checkpoint /shared/ember/experiment_001/A_round1/best.pt \
  --config /shared/ember/experiment_001/candidate_A.json --split val \
  --output /shared/ember/experiment_001/A_validation --device cuda
```

Compare A and B validation reports using a pre-agreed accuracy/time criterion.
For the selected candidate only, repeat with `--split test` and a new output folder.
Reports include per-region and pooled metrics, newly burned-area metrics, persistence,
arrival MAE and timing scopes. Empty-mask IoU=1; inspect empty counts and recall.
Burn score is not a calibrated physical probability unless separately validated.

## 6. Unlabeled demo predictions

```bash
python3 experiments/parallel_surrogate_training/predict.py \
  --checkpoint /shared/ember/experiment_001/A_round1/best.pt \
  --input /shared/prepared/new_scenario_inputs.npz \
  --output /shared/ember/demo_prediction --device cuda
```

No target or simulator call is required here. Outputs are NPZ predictions plus JSON.
`conditional_arrival_seconds` is meaningful with the burn score/mask; display arrival
uses NaN outside predicted burn. Preserve numeric arrays for the presentation.
All output directories must be new to avoid clobbering results.

## 7. Fair cluster experiment

Use the same initial pool, predetermined simulation queue, candidate configurations,
fixed validation set and elapsed-time budget. One-node baseline may overlap CPU
simulation and GPU training and schedule both candidates sequentially.
Record best validated PHYSICAL metric versus elapsed time, successful labels,
completed experiments, node-hours, and actual CPU/GPU activity. More hardware is
not guaranteed to improve accuracy; report measured results only.

`events.jsonl` provides host wall-clock training events, not cluster utilization.
Synchronize host clocks for cross-node timelines. `peak_torch_allocated_bytes` is
not total unified-memory usage. Capture Fuzzball placement/job times and system GPU
and CPU telemetry separately. Inference timings exclude checkpoint startup; forward
timings cover only the first sample with batch size 1. End-to-end includes export.

## Verified here versus still required

Local synthetic checks can run with `verify_handoff.py`; CPU fixtures are code tests,
not production model training. Real ForeFire export, spatial correctness, CUDA on
GB10, shared-volume behavior, Fuzzball placement, contention and performance must
be verified on the cluster. No automatic scheduler, DDP or elastic workers are included.
