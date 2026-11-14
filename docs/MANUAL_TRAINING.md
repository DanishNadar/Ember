# Manual experiments in Ember Observatory

No notebook cell submits a workflow by default. The only submit function is
`manual.launch(..., confirmation=EXACT_NAME, dry_run=False)`. Opening, replaying,
preflight, preview, preparation, retrieval and export do not start compute.

## Open the integration notebook

Until PR #10 is approved and merged, use its integration worktree. Do not copy
over the dirty primary checkout or its historical executed notebook. From the
`HPC_Hacks` directory on Windows:

```powershell
cd ../Ember-integration-review-20261114
python -m pip install -r notebooks/requirements.txt
python -m jupyterlab notebooks/Ember_Observatory.ipynb
```

Install a CPU PyTorch build in this environment if absent: preflight needs
dataset/checkpoint inspection, but it never runs a model. In WSL, from the same
`HPC_Hacks` directory:

```bash
cd ../Ember-integration-review-20261114
python3 -m pip install -r notebooks/requirements.txt
python3 -m jupyterlab notebooks/Ember_Observatory.ipynb
```

Use `git worktree list` to find the integration worktree if opened elsewhere.
After an authorized merge and safe synchronization, use the canonical Ember
checkout instead. Existing private experiment-root registration lets the current
Windows notebook find the preserved pilot in the canonical artifacts directory.

## Configure, preflight, preview

Run setup and the **Manual experiments** configuration cell. Set `DATASET` to a
real root containing `train`, `val`, `test` NPZ directories, with sibling
`baseline.yaml` and `dataset_manifest.json`. The verified pilot has 96/24/24
samples and 19 channels. The 26k source starts are not a labeled training dataset.

Edit `OPTIONS`: fresh experiment name, output root, dataset, and supported
hyperparameters in `OPTIONS['config']`. Modes are `single` or `independent`
(exactly two learning rates in `trial_learning_rates`). Adam is the existing
optimizer. A trusted optional checkpoint is **inspected for compatibility only**;
it does not initialize fresh training. Fine-tuning/DDP submission is blocked:
the existing DDP recipe requires a separately verified network rendezvous.

Set `RUN_PREFLIGHT=True`. Leave `CHECK_REMOTE=False` for local validation; set it
true for read-only authentication and resource checks. Before inputs are staged,
use `REQUIRE_INPUTS=False`; use true afterward. Inspect the printed configuration,
dataset hash, epochs, job counts, resources, new-label flag and output destination.
Capacity is a point-in-time fit estimate, not a placement guarantee. GPU memory
needs depend on model/batch size; the workflow's 16 GiB request is not a model fit
proof. CPU physics is off by default. If enabled, it uses two shards, configured
workers per shard and a scenario cap **per region across shards**; provide an
existing physics archive URI made by `orchestration/observe/package_physics.py`.

## Prepare, stage, deliberately launch

Set `PREPARE_RUN=True` once to create `RUN`, a new immutable local run folder.
Do not rerun with the same name. Preparation packages existing genuine samples
and source, saves configurations, manifest hashes, architecture, Git SHA/dirty
state and `workflow.fz`. No job or upload occurs. Set it back to false.

Set `STAGE_INPUTS=True` once to upload the new input object, then false again.
No workflow is submitted. The CLI must be authenticated in your chosen shell:

```powershell
wsl --exec sh -lc '$HOME/.local/bin/fuzzball context show'
```

```bash
~/.local/bin/fuzzball context show
```

On Windows the notebook discovers the WSL CLI through the WSL user's home; no
personal Linux path is required. Validate the preview explicitly if desired:

```python
manual.command('workflow', 'validate', manual.cli_path(RUN / 'workflow.fz'))
display(manual.launch(RUN))  # dry-run; never submits
```

Only when you personally want to spend compute, set `CONFIRM_LAUNCH=True` and run
the separate launch cell. It requires the exact experiment name, fresh preflight,
matching staged digest and workflow validation. It records a submission-attempt
marker before sending the request and the returned workflow ID afterward.
Immediately reset `CONFIRM_LAUNCH=False`. A saved true guard is not safe to share.

## Watch, retrieve, visualize, export

Put the returned `SUBMISSION['ID']` and exact job names from
`manual.preview(OPTIONS)['jobs']` into `WORKFLOWS` in the live section. Enable
`START_LIVE_WATCH=True` explicitly. Separate job curves show the recorded metrics;
progress includes learning rate, throughput, elapsed time, checkpoint epoch and
epoch-based remaining-time **estimates** when enough data exist. Scheduler errors
are fetched separately. Phase timelines show observed computation intervals, not
container lifetimes; unrecorded nodes and telemetry remain unrecorded.

When complete, run `RESULTS = manual.retrieve(RUN)`. This only retrieves artifacts,
checks archive hashes and binds workflow/job identity; it cannot launch jobs.
Register `RUN` as an experiment root or set `EMBER_RUNS_DIR` to its parent.
Replay histories and gallery cells and save the notebook. The remote job performs
one final held-out evaluation after validation-loss checkpoint selection.

For additional **deliberate** gallery evaluation of a trusted completed checkpoint:

```python
# Command preview only; execute it yourself when evaluation is intended.
print(['python', 'ml/export_gallery.py', '--checkpoint', 'PATH_TO_BEST_PT',
       '--dataset', str(DATASET), '--output', 'FRESH_GALLERY_DIRECTORY',
       '--split', 'val', '--limit', '1', '--device', 'cpu'])
```

Use `--split test` for final reporting only. Never select models or repeatedly
tune thresholds on test results. Existing galleries provide actual/predicted
arrival, ignition, TP/FP/FN masks and per-horizon overlap and recall.

```powershell
python scripts/export_observatory.py --notebook PATH_TO_SAVED_NOTEBOOK --experiment-id EXPERIMENT_NAME
```

Inspect the new version and manifest before requesting approval to publish.
The explicit publisher accepts `--publish-manifest`, `--approve-sha256` and a new
`--publish-branch reports/observatory-UNIQUE`; it adds a publication receipt without
changing approved snapshot bytes. Publishing provides snapshot access, not live
access to local files.

## Recovery

- Missing input object: stage the prepared input; inspect its digest. Never force
  overwrite an older prefix. Missing physics input blocks physics-enabled runs.
- Resource fit failure: reduce jobs/workers or wait. Team visibility is not a
  grant to use other teams' resources. Scheduler availability can change.
- NFS provisioning failure: use existing `team15-scratch`, not the broken NFS path.
- Invalid checkpoint contract: keep its original channels/architecture/units and
  train-only normalization. Do not alter a checkpoint to silence validation.
- Submission timeout: inspect `workflow list` for the exact unique name before
  doing anything else. The attempt marker prevents automatic duplicate submits.
- Existing output: choose a fresh name; never reset, clean or overwrite results.

Historical evidence: the real two-epoch workflow
`ba78b08b-632e-4de8-9d4b-fcb7e105c61e` verified CPU ForeFire, one GB10, telemetry
and artifact egress. Container overlap was 15.34 s; observed physics/training
phase overlap was zero. True multi-node DDP remains unverified.
