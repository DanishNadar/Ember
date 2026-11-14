# Fuzzball arrival pilot

This experiment uses the existing `ml/train_arrival.py` entry point and unchanged
two-head U-Net. The original checkout and its untracked Fuzzfiles are preserved.
Work is isolated on `codex/fuzzball-arrival-20261114`, based on remote main commit
`3d4c8ffdaae8da49c6c567716b4b62f36b7c5911`.

The original 905-byte archive contained only `model.py`. Its requested object,
`fb://user/ember/arrival-run01-input.tgz`, did not exist. Uploading that incomplete
archive would not have fixed training.

## Data and scientific scope

The latest repository contains 26,000 input scenarios but no corresponding
training labels. `build_pilot.py` runs the repository's ForeFire wrapper with
ForeFire 2.6.0 to produce a bounded, genuine simulator pilot. Each simulation runs
in a fresh process. All meteorological inputs come from the existing scenario
rows; no mock targets or invented weather fields are used.

- Train: 24 simulations each from Corsica, SoCal, NorCal and Great Basin.
- Validation: 24 simulations from Texas Panhandle.
- Test: 24 simulations from Montana.
- A whole region is one conservative scenario family and appears in one split.
- Arizona remains unused. This pilot does not reproduce the full mixed-region
  evaluation protocol or the 26,000-scenario dataset.
- Grid: 320 × 320 at 40 m, 3,600-second horizon, native `[x east,y north]` axes.
- Inputs: the 19 physical channels from `ember_bench.initstates`, including both
  wind vectors, shift timing, ignition, and simulator-engine identity. The fixed
  1,800-second wind ramp is recorded in sample metadata.
- Unreached cells use -9999 and are censored at the horizon. Edge-hit simulations
  are excluded. Every accepted sample has a SHA-256 hash and provenance record.
- The documented ForeFire Farsite downslope limitation remains. Results describe
  agreement with this simulator, not observed wildfire prediction accuracy.

Training keeps the configured 30 epochs, batch size 4, 16 base filters, depth 3,
and baseline learning rate 0.001. The second experiment changes only the learning
rate to 0.0003. Each run uses a fresh output directory. Variant selection must use
validation loss; test metrics are final reporting only.

## Reproduction

Create an isolated Linux environment with ForeFire 2.6.0, NumPy, netCDF4 and PyYAML.
No local PyTorch installation is required for dataset generation or packaging.

```text
python orchestration/fuzzball/build_pilot.py --output UNIQUE_DIRECTORY --source-commit COMMIT --workers 4
python orchestration/fuzzball/prepare_experiment.py --dataset UNIQUE_DIRECTORY --prefix UNIQUE_OBJECT_PREFIX
```

`prepare_experiment.py` checks counts, sample hashes and split identities; creates
a source/data archive with per-member hashes; and emits a one-GPU initial workflow
and a two-job parallel workflow. Upload using the installed CLI's supported syntax:

```text
fuzzball object put INPUT_ARCHIVE fb://user/ember/UNIQUE_OBJECT_PREFIX/input.tgz --ttl 30d
fuzzball object describe fb://user/ember/UNIQUE_OBJECT_PREFIX/input.tgz --output json
fuzzball workflow validate FUZZFILE
fuzzball workflow start FUZZFILE --name UNIQUE_WORKFLOW_NAME --output json
```

Check that the remote size/digest match before submission. The verified container
tag is `nvcr.io/nvidia/pytorch:26.10-py3`; its ARM64 manifest digest is recorded in
the package manifest. The job verifies CUDA with an actual kernel, checks package
hashes, uses the original training/evaluation CLI, and records hardware, wall time,
history, validation results, checkpoint hashes and measured inference latency.

Retrieve each result archive with `fuzzball object get`, verify its digest, and
extract to a new directory. Keep the input package with the results for exact
dataset reproduction. `runs/` and `packages/` are ignored artifacts.

The first submitted workflow (`aa6f2ba4-17cf-44cd-82d4-302d366749dc`) prepared
the ARM64 image but failed before training because the Team 15 NFS mount returned
`mount.nfs: Operation not permitted`. The `*-scratch.fz` workflows use the
already-configured `team15-scratch` local NVMe provisioner instead. Inputs and
outputs still use the verified object cache; no cluster configuration was changed.

The first dataset-generation attempt produced samples but failed to record its
Git commit because Linux Git cannot read a Windows worktree pointer. It is
preserved under `arrival-pilot-20261114-01`; the verified dataset is `-02`.
Explicit commit capture fixes the cross-platform issue without modifying Git
configuration.
