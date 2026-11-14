# Canonical development and scientific result snapshots

Use `HPC_Hacks/Ember` as the primary development checkout. The pilot and
Observatory folders are worktrees of the same Git repository, not separate
repositories. Preserve them while their source changes and artifacts are reviewed.
The integration branch combines current team main, the verified pilot, and the
Observatory implementation; it must be reviewed before merging to main.

## Git across Windows and WSL

The local administrative paths were repaired with the supported command:

```text
git worktree repair --relative-paths ../Ember-fuzzball-20261114 ../Ember-observatory
```

This was verified with Git 2.48.1 for Windows and Git 2.50.0 in WSL. Use a Git
version supporting relative worktrees. Do not repair paths by repeatedly writing
Windows absolute paths from one shell and Linux absolute paths from the other.
The repository-local `core.autocrlf=true` makes existing CRLF worktree files agree
across these clients. `.gitattributes` establishes LF for source going forward,
while existing CSV bytes are preserved. Do not renormalize datasets or teammates'
presentation files as a side effect of synchronization.

Before changing a dirty checkout, preserve actual files and ignored results in a
verified backup outside every worktree. A stash is not a dataset/checkpoint backup.
Use ordinary fetch/fast-forward operations only when changed paths do not overlap
local edits. No resets, cleans, force pushes, or worktree pruning are needed.

## One place for experiments

Use `artifacts/experiments/<experiment-id>/` under the primary checkout for new
generated data and retrieved result bundles. Preserve unique per-job output
directories, source manifests and hashes. Never overwrite a previous experiment.
These data and checkpoints are ignored by Git; keep approved artifact-storage
copies as well. Existing version-controlled input assets and scenario tooling
remain under `dataset/`.

Create an optional **local, ignored** `artifacts/local/observatory.json`:

```json
{
  "experiment_roots": ["artifacts/experiments"],
  "notebook_roots": ["notebooks"]
}
```

During migration, this local file can register the existing executed notebook
directory without replacing it. Absolute machine paths belong only in this
ignored config, not shared source. `EMBER_RUNS_DIR` overrides experiment discovery
when an authorized artifact directory is elsewhere. Future notebook runs and
exports use the canonical checkout and the same experiment location; no repeated
manual copying between worktrees is required.

## Notebook and explicit export

Install the display/export dependencies in the notebook environment:

```text
python -m pip install -r notebooks/requirements.txt
```

Open `notebooks/Ember_Observatory.ipynb`, select a Python kernel, run the replay
cells, and **save the notebook with its outputs**. No local PyTorch or GPU is
required for replaying CSV metrics and saved figures. Live monitoring remains
explicitly disabled until real workflows are configured.

```text
python scripts/export_observatory.py
```

The exporter locates the newest saved executed notebook in the configured roots.
It requires valid outputs, rejects recorded errors unless `--allow-errors` is
explicit, and identifies the experiment from available evidence. Use
`--experiment-id ID` if several experiments are present or `--notebook PATH` to
select a particular saved file.

Every invocation creates a fresh directory under
`reports/observatory/<experiment-id>/<UTC-version>-<notebook-hash>/` containing:

- A sanitized executed notebook snapshot and a self-contained HTML report.
- Deduplicated saved PNG visualizations, numerical JSON, and per-run CSV histories.
- Git SHA/dirty state, exact original notebook hash, workflow IDs, dataset
  provenance, saved-file time, and execution time only where actually recorded.
- A checksum manifest and an adjacent ZIP suitable for an authorized file upload.

This reads saved outputs; it does not execute cells, train a model, submit a
Fuzzball job, or publish to GitHub. Previous reports and the original notebook are
preserved. Home paths, private IPs and recognizable credentials are removed from
text/metadata. Inspect the preview and image contents before approving publication.
The exact unredacted historical notebook remains in the private backup.

## Explicit approved publication

After reviewing the concrete snapshot and approving its manifest hash:

```text
python scripts/export_observatory.py --publish-manifest PATH_TO_MANIFEST_JSON --approve-sha256 APPROVED_SHA256 --publish-branch reports/observatory-UNIQUE
```

The command verifies every artifact again, rejects main and existing branches,
and pushes only that snapshot on a fresh `reports/observatory-...` branch based on
current origin/main. A temporary index protects all staged/unstaged team work.
It never changes main, force-pushes, merges a PR, or includes checkpoints/raw data.
The returned immutable GitHub URLs identify the Markdown index, downloadable
HTML, executed notebook and metrics. HTML is an offline report file, not a newly
hosted website. Publishing code for review is a separate integration-branch/PR step.

ChatGPT's GitHub connection can read the **published snapshot** through its exact
GitHub URL/ref. Alternatively, upload the generated ZIP or selected report files.
Publication does not grant live filesystem access; unsaved notebook state and
unpublished local changes remain outside that snapshot. Export and publish again
explicitly when newer outputs should become visible.

## Checks and scientific boundaries

```text
python -m unittest scripts.test_export_observatory scripts.test_arrival_checkpoint orchestration.observe.test_observatory -v
python -m unittest discover -s tests -v
```

From `ml/`, `python -m unittest test_contract -v` and
`python smoke_test.py --config config.yaml` exercise the original CPU pipeline.
The smoke test is explicitly synthetic and is not scientific accuracy evidence.
Fuzzball YAML can be validated with the authenticated CLI without submitting jobs.

Histories and progress are keyed by workflow/experiment **and job and epoch**.
CPU/GPU plots use one shared UTC time origin and omit invalid/missing readings.
Node clock synchronization still matters. CPU measurements use a recorded 100 ms
host sampling window; GPU values are driver-reported snapshots. Neither establishes
whole-job average utilization. Summed epoch duration fractions are work accounting,
not proof of a wall-clock bottleneck across overlapping jobs.

Test data remain separate from training/validation. New checkpoints record split
identities; evaluation and DDP resume check units, model contract, train-only
normalization and historical family separation. Historical pilot sidecars remain
supported; missing legacy identities produce an explicit warning, not a claim of
verified historical independence. DDP resume retains checkpoint normalization.

The executed pilot used 144 genuine ForeFire simulations and four/one/one region
families. The validation-selected baseline has 0.329 validation IoU and 0.759 test
IoU, across different regions; this is not a significance or generalization claim.
Conditional arrival MAE omits missed fire cells. Expand independent geographic
validation, report overlap with arrival error, and investigate class imbalance and
known simulator limitations before operational claims. The 26,000 source starts
still require labels for full-dataset training. Independent two-GPU experiments
are verified; new CPU/GPU overlap instrumentation and actual NCCL DDP execution
remain future runtime checks. No new GPU training is needed for consolidation.
