# Ember: direct fire-arrival-time surrogate (experimental branch)

This is an **alternative** to the existing `train.py` next-state U-Net, which remains unchanged.
It predicts a fire's complete 60-minute arrival field from its initial ignition,
fuel/weather inputs and **known prescribed future wind schedule**, without
autoregressive feedback. It approximates ForeFire, not observed wildfire truth,
and is not a governing-equation PINN.

## Intended input dataset

One `.npz` for each *full* ForeFire simulation, not one per frame:

```text
ml/data_arrival/
  train/run_*.npz
  val/run_*.npz
  test/run_*.npz
```

Required keys:

| Key | Shape / interpretation |
|---|---|
| `x` | float32 `[C,320,320]`; channels exactly as configured |
| `arrival_time_seconds` | float32 `[320,320]`; 0–3600 for reached cells; -9999 for unreached |
| `channel_names` | Unicode array of exact configured channel names |
| `simulation_id` | Scalar Unicode, stable ID of the run |
| `scenario_family_id` | Scalar Unicode, groups related weather/ignition variations for leakage-free splits |
| `dataset_kind` | Scalar Unicode `forefire` |
| `horizon_seconds` | Scalar numeric, 3600 (or matching config) |
| `cell_size_meters` | Scalar numeric, e.g. 40 |

Set correct grid size, horizon and channels in `arrival_config.yaml`. Every input
must align in projection, orientation, resolution and time with the arrival grid.
The loader checks arrays but cannot verify coordinate reference transformations.

In the default config, channels are `ignition_mask`, `wind_u_mps`,
`wind_v_mps`, `fuel_moisture`. These are **proposed** and must be changed
to match actual simulator output. Global scalars can be broadcast across the grid.
**If wind changes mid-simulation, encode BOTH pre/post wind vectors and the shift
time** as additional channels; a single mean wind is insufficient.
Encode fuel categories as a fixed one-hot vocabulary (never raw arbitrary integer IDs).
Never silently substitute unavailable environmental fields with fabricated zeros.

**Unreached cells are right-censored at the horizon.** The network learns both
(i) whether a cell burns by 60 minutes and (ii) conditional arrival time for
reached cells only. For rendering the forecast at horizon `h`, threshold
`sigmoid(burn_logits)` and require estimated arrival time <= h. This combines
classification and regression, and may show inconsistent masks if predictions
are poorly calibrated; validate at each forecast time.

Run from `ml/` after PyTorch, NumPy and PyYAML are installed:

```bash
python train_arrival.py train --config arrival_config.yaml
python train_arrival.py evaluate --config arrival_config.yaml --checkpoint outputs_arrival/best.pt
```

Metrics: held-out **IoU for burned-by-horizon** and **arrival-time MAE only on
cells ForeFire says were reached**. Arrival MAE alone does not penalize missed fire
cells, so report both. The test split is not used for checkpoint selection.

## Integration prerequisites / nonclaims

1. ForeFire team must supply real numeric arrival grids and every varied input,
including wind shifts and their timing. Existing reference KML snapshots and
zero-pair dataset manifests cannot fill this contract.
2. `grid_size=320`, `cell_size_meters=40` implies 12.8 km per side; check the
simulation's actual geometry. Do not upscale 128x128 masks and claim new physics.
3. Different simulation runs from the *same scenario family* must stay in one
split. For geographic generalization, reserve whole landscapes as a separate test.
4. Run benchmark on target hardware; do not claim an inference speedup from code
presence. Log dataset generation, training cost, throughput and wall clock.
5. No CPU/GPU training, ForeFire integration or accuracy tests were executed by
the connector authoring this branch. A teammate must run the commands and tests.
