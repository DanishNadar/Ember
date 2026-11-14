# Ember ML surrogate

A compact **supervised PyTorch U-Net** predicts the cumulative burned-area mask at
`t + forecast_horizon_seconds` from numeric raster channels at `t`. It is not a
PINN. The optional monotonicity loss is physical regularization, not a residual of
a governing equation. This component does not run ForeFire or implement Fuzzball.

## Repository inspection and scope

Before implementation, the Ember Git working tree was clean. Existing code under
`src/simulation`, `src/processing`, `src/analysis`, `scripts`, and `tests`, the
vendored `forefire/` checkout, and all existing artifacts were inspected or
inventoried and left unchanged. The root README and requirements belong to the
extraction pipeline and were also left unchanged. All additions are inside `ml/`.

The current `src/processing/dataset_builder.py` writes aggregated `train.npz`,
`validation.npz`, and `test.npz` with `current_burned_mask` / `next_burned_mask`
keys. Those files are **not this ML contract**. The checked-in dataset manifest
reports no valid temporal pairs, so it cannot train this model. The simulator team
must export the per-sample contract below; this implementation does not alter
their builder or silently convert reference artifacts into training labels.

## Install and run

Run commands from `Ember/ml`:

```powershell
cd Ember/ml
python -m pip install -r requirements.txt
python -m unittest test_contract -v
python smoke_test.py --config config.yaml
```

If already in `Ember`, use `cd ml`. A suitable PyTorch build must exist on the
target host. Requirements do not select a CUDA wheel or install drivers. On the
ARM64 NVIDIA environment, keep its installed PyTorch build; dependency installation
without `--upgrade` should leave a compatible build in place. `device: auto` uses
CUDA only when `torch.cuda.is_available()` is true; otherwise it uses CPU.

The smoke test creates a separate, complete config and artifacts under
`.smoke_test/run_*/`. It explicitly uses a 32-pixel grid, 4 base filters, 2 pooling
stages, 2 epochs and CPU so it runs quickly. These fixture choices are recorded in
that generated YAML. It exercises actual command-line entry points, best and
periodic checkpoint writing, checkpoint reloading, evaluation, plots, and
prediction on an **unlabeled** NPZ. Its expanding circles are SYNTHETIC/MOCK, have
no physical calibration and must never be used as a ForeFire accuracy benchmark.
No mock accuracy threshold is a test assertion.

After numeric ForeFire data are available, edit `config.yaml` to match the actual
channel definitions, horizon, grid and paths, leave `dataset_kind: forefire`, then:

```powershell
python train.py --config config.yaml
python evaluate.py --config config.yaml --checkpoint outputs/best.pt
python predict.py --config config.yaml --checkpoint outputs/best.pt --input path/to/sample.npz
```

Paths inside YAML resolve relative to its location. CLI checkpoint and input
paths resolve relative to your shell's working directory. Every training run
requires a fresh or empty `output_dir`, protecting prior checkpoints. Evaluation
and prediction replace artifacts with the same names in their output subfolders;
use a different `output_dir` to retain multiple evaluations/thresholds. No script
modifies the input dataset. Hyperparameters and I/O settings are documented beside
every option in the central `config.yaml`; unknown/missing keys are rejected.

## What the simulator team must export

Use this layout (one temporal pair per file):

```text
data/
  train/*.npz
  val/*.npz
  test/*.npz
```

Each NPZ must contain:

| Key | Format / meaning |
| --- | --- |
| `x` | float32 `[C,H,W]`, finite numeric inputs at `t` |
| `y` | float32 `[1,H,W]`, exactly 0/1 cumulative burn at `t + delta_t` |
| `channel_names` | Unicode string array `[C]`, exact order of `config.channel_names` |
| `simulation_id` | Scalar Unicode string, unique identity of a whole simulation |
| `scenario_family_id` | Scalar Unicode string grouping related runs, ignitions, parameter variants, etc. |
| `dataset_kind` | Scalar Unicode string, `forefire` for real simulator exports, `synthetic_mock` for fixtures |
| `time_t_seconds` | Scalar finite nonnegative number, time at current state, seconds, when available |
| `forecast_horizon_seconds` | Scalar positive number, seconds, when available; must match config |
| `cell_size_meters` | Scalar positive number, meters, when available; square cell width |

The first six entries are required for training/evaluation and split auditing.
`scenario_family_id` may be renamed using `split_group_key`; it must still group
all related scenarios. For a genuinely independent simulation with no relatives,
its family ID may equal its simulation ID. IDs must be globally stable, including
across re-exports. Prediction requires only `x` and `channel_names`; available
metadata are validated and carried to its output. `y` may be omitted at prediction.
Use scalar Unicode/numeric NPZ metadata, not Python dictionaries/object arrays or
pickled objects. Extra scalar metadata (e.g. coordinate reference system) survive
in prediction metadata. Missing horizon metadata means the export is assumed to
use the configured horizon; include the metadata to allow automated verification.

Example export, with `current_mask` and `future_mask` supplied by the simulator:

```python
import numpy as np

np.savez_compressed(
    "data/train/scenario001_t000.npz",
    x=current_mask.astype(np.float32)[None, :, :],
    y=future_mask.astype(np.float32)[None, :, :],
    channel_names=np.asarray(["burned_mask"]),
    simulation_id=np.asarray("scenario001_run01"),
    scenario_family_id=np.asarray("scenario001"),
    dataset_kind=np.asarray("forefire"),
    time_t_seconds=np.asarray(0.0),
    forecast_horizon_seconds=np.asarray(60.0),
    cell_size_meters=np.asarray(10.0),
)
```

Create the parent directories before export. Mask geometry, environmental fields
and targets must share grid extent, orientation, projection and resolution. The
loader checks shape but cannot detect geospatial misalignment. It deliberately
does not resize: rasterize/resample correctly on export. Missing/invalid physical
values must be resolved explicitly; NaN/inf and fractional burn labels are errors.
For cumulative masks, previously burned cells must remain burned in the target.

**Do not infer labels from PNG colors.** Supply numeric arrays or rasterized
geometric masks, ideally from numeric ForeFire arrival times: a valid reached
cell with arrival time <= `t` is burned, and <= `t + delta_t` gives the future
mask. Handle the engine's actual unburned/no-data sentinel explicitly before
thresholding; negative sentinels must not become burned. A front line alone does
not necessarily describe cumulative burned area. ForeFire probabilities are not
assumed or needed. Only the network produces probabilities.

## Channels, normalization and leakage

The default is **only** `burned_mask`. Environmental fields are unconfirmed.
Add fields only once the team exports them and records their units and meaning
(for example, actual exported `wind_u_mps`, `wind_v_mps`, elevation in meters).
Set the exact ordered `channel_names` and corresponding `channel_types` together;
the model infers `C`. Use `continuous` for actual continuous fields and `binary`
for burn or one-hot masks. Raw fuel-category indices must not be scaled as if they
were measurements: the supported representation is one binary channel per fuel
category, with a fixed, documented vocabulary and explicit other/unknown category
if needed. The exporter must enforce mutually exclusive fuel membership; the
generic loader validates each binary channel but cannot infer which channels
constitute a categorical vocabulary.

Continuous inputs use pixel-weighted training-set mean and population standard
deviation. Constant channels are centered and use standard deviation 1. Binary
channels pass through unchanged. `normalization.json` is written once and embedded
in checkpoints; evaluation and prediction load and compare it, never refit it.
Ship the JSON beside the checkpoint. Channel definitions, architecture, horizon
and dataset kind must match the checkpoint. Threshold, device and evaluation
output paths may change without retraining.

Split entire scenario families **before** writing files; roughly 70/15/15 percent
of independent families is a possible starting policy, not a required ratio.
Never randomly split temporal pairs from the same simulation, including nearby
time windows. The `precreated` policy accepts only `train`, `val`, `test`; all
three must be nonempty. Every training/evaluation command checks all files and
rejects simulation IDs or family IDs shared across directories. This structural
audit of test metadata/validity does not use test labels for scaling, losses,
model selection or early stopping. Evaluation also compares test IDs against the
checkpoint's saved training/validation manifest, preventing a changed data root
from bypassing the held-out check. Keep `split_manifest.json` beside the checkpoint
for evaluation. False or missing family identities cannot be repaired by ML code.

## Model, loss and saved artifacts

The U-Net uses two padded 3x3 convolutions plus ReLU per stage, 2x2 max pooling,
transposed-convolution upsampling and skip concatenation. Filter counts double at
each pooling stage. There is no pretrained download or normalization-layer batch
dependency. A 1x1 output convolution returns `[B,1,H,W]` raw logits; image sides
must be divisible by `2**depth`. Dropout is configurable and disabled in eval.

Loss = `bce_weight * BCEWithLogitsLoss + dice_weight * soft_dice_loss +
monotonicity_weight * mean(relu(current_burn - sigmoid(logits)))`.
Soft Dice is computed per sample, then averaged; its smoothing is configurable.
BCE never receives a sigmoid output. Monotonicity is optional and defaults to 0;
even with a positive weight it encourages preservation rather than guarantees it.
There is no hard postprocessing to conceal monotonicity errors.

Training saves:

- `best.pt`: lowest validation-loss model, optimizer state, epoch, config and statistics.
- `last.pt` and `epoch_NNNN.pt`: latest and configured periodic checkpoints.
- `normalization.json`, `config_used.yaml`, `split_manifest.json`: reproducible input definitions and provenance.
- `metrics.csv`: epoch train/validation loss, micro confusion metrics and area error.

Early stopping uses validation loss, patience and minimum improvement from config.
Best checkpoint selection still retains the actual lowest observed loss. Seeds,
loader shuffling and deterministic-kernel requests are set explicitly. Exact
results can still differ across PyTorch versions and hardware. Checkpoints contain
optimizer state for inspection/future integration; automatic resume is not
implemented. Current loaders reread NPZ files for simplicity; split auditing also
reads every sample, which may need optimization for very large datasets.

Evaluation saves `evaluation/metrics.json`, `evaluation/comparison.png` and
`evaluation/predictions/*.npz`. Synthetic evaluation inserts a `synthetic_mock/`
subdirectory and marks JSON and figure as mock. Prediction saves
`predictions/<input_stem>_prediction.npz` (also separated for mock runs) containing
float32 `probability [1,H,W]`, uint8 `predicted_mask [1,H,W]` and a scalar
`metadata_json` string. Evaluation NPZs additionally retain the current and target
masks and input metadata. The trained checkpoint stays in the training output.

IoU, Dice/F1, precision and recall use summed held-out pixel confusion counts
(micro aggregation), with `probability >= threshold`. A metric with a zero
denominator is defined as 1 (including both-empty masks); confusion counts are
also saved so this convention is visible. Burned-area absolute error is the mean
over samples of `abs(predicted_burned_pixels - target_burned_pixels)`; it measures
area, not overlap, so it may be zero despite location errors. With square-cell
sizes for every sample, a corresponding mean error in m² is saved; otherwise it
is null. Training CSV m² is null because training metrics do not load cell sizes.
The comparison image shows current burn, ForeFire target, network mask, and signed
error (red false positives, blue false negatives).

Latency is repeated forward inference on the first test batch, after configured
warmups, with tensors resident on the device. CUDA is synchronized before and
after each timed forward. Mean/median batch milliseconds, actual batch size and
amortized milliseconds per sample are recorded. This excludes disk reads,
preprocessing, transfers, sigmoid and output writing; it is not end-to-end or
batch-size-one latency unless the actual batch size is one.

## Verification and limits

`test_contract.py` checks malformed shapes/dtypes, NaN/inf, binary targets,
channel ordering, horizon consistency, synthetic provenance, missing data,
simulation and family leakage, train-only statistics, unchanged one-hot channels,
constant fields, known metric counts, model output shape and regularizer gradients.
It also checks config typos/missing options, checkpoint/config/statistics identity,
and held-out leakage against the original checkpoint manifest after changing data.
`smoke_test.py` verifies actual training, checkpoint loading and deterministic
reload predictions, held-out evaluation and unlabeled inference with mock data.

Real ForeFire training/evaluation, useful generalization, geospatial correctness,
environmental-field availability, forecast horizon choice, NVIDIA CUDA execution,
and the target ARM64 NVIDIA machine remain untested until those data/hardware are
available. Report results as **agreement with ForeFire labels**, never real-world
fire prediction accuracy. Default hyperparameters are starting points, not a
validated scientific configuration.

Local verification on 2026-11-14: PyTorch 2.9.0+cpu; the contract tests and full
2-epoch CLI mock smoke test passed. The default 128x128, one-channel, 16-base-filter,
depth-3 model has 481,745 parameters and passed a forward/backward check. Its
generated comparison PNG was visually inspected. CUDA was unavailable locally.

## File changes

All new files: `.gitignore`, `README.md`, `requirements.txt`, `config.yaml`,
`config.py`, `model.py`, `dataset.py`, `common.py`, `train.py`, `evaluate.py`,
`predict.py`, `mock_data.py`, `smoke_test.py`, `test_contract.py`, all under `ml/`.
Generated smoke data, checkpoints, CSV/JSON/NPZ outputs, figures and Python caches
stay in ignored paths. No pre-existing file was modified.
