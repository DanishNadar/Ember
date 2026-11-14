# Ember initial states v1 (Corsica / Aullène)

Fire starts on ForeFire's real Aullène landscape (`data_real/aullene/data.nc`). These are inputs
only: no ForeFire labels yet. ForeFire (labels) and the neural net (input tensor) read the same
row, so both see identical conditions.

Built by `python -m ember_bench.initstates build --out ember_init_v1` from
`configs/init_corsica.json`. Regenerating with the same config gives the same samples.

## Splits

| split | samples | where the window can be |
|---|---|---|
| `train` | 10,000 | fully outside the holdout box |
| `val` | 1,000 | same, other seed |
| `test` | 1,000 | same, other seed (new weather and ignitions on terrain that training has seen) |
| `test_ood` | 1,000 | fully inside the holdout box (terrain never seen in training) |

The holdout box (`holdout_box_m`) is the southern 16 km of the tile. The rule holds for any
labelling window up to `max_window_m` = 12.8 km centred on `crop_cx, crop_cy`. A bigger window
can overlap the holdout box.

## How a sample is drawn

* Every continuous knob is a Latin-hypercube sample over the range in the config. Defaults span
  ForeFire's valid range (wind 0–20 m/s, any direction, shift ±180° at any time in the run,
  moisture 0.02–0.29 with extinction at 0.30).
* The ignition is uniform over burnable ground of the whole tile (rejection sampling on the
  10 m fuel map). The window is then placed so the ignition sits at (`ign_win_x`, `ign_win_y`) of
  the 12.8 km reference window.
* Ignition shape: half `point` (ForeFire `startFire`), half `ellipse` (a burning area that is
  already alive: semi-axes `ign_a_m`, `ign_b_m`, orientation `ign_orient_deg`, given to ForeFire
  as a clockwise `FireFront`). A thin ellipse is a line ignition.

## Files per split

* `samples.csv`: one row per sample (columns below).
* `scenarios.jsonl`: one ForeFire-ready scenario per line at the reference grid (320 × 40 m,
  60 min), so `sim.run_scenario(json.loads(line))` runs it. For another grid, call
  `initstates.to_scenario(row, cfg, grid={"n":…, "dx_m":…, "horizon_s":…})`.
* `meta.json`: config, channel list, conventions.

Fuel and terrain layers are not stored (they would be about 1.6 GB). They are cropped from data.nc
on the fly, deterministically, about 20 ms per sample. Add `--layers` to store them on local
disk.

## `samples.csv` columns

| column | unit | meaning |
|---|---|---|
| `sample_id`, `split`, `seed` | | stable id, split, per-sample seed |
| `crop_cx`, `crop_cy` | m | window centre in data.nc's frame (x east, y north from the SW corner) |
| `ign_x_m`, `ign_y_m` | m | ignition centre, same frame |
| `ign_shape` | | `point` or `ellipse` |
| `ign_a_m`, `ign_b_m`, `ign_orient_deg`, `ign_aspect` | m, m, deg | ellipse semi-axes (b = max(a·aspect, dx/2)); orientation of a, anticlockwise from +x. 0 for points |
| `wind_speed` | m/s | given to ForeFire as is (CORSICA_NATIVE applies windReductionFactor 0.4 inside Rothermel) |
| `wind_dir_deg` | deg | direction the wind blows **toward**, 0 = north (+y), 90 = east (+x). Meteorological "from" = +180 |
| `wind_shift_deg` | deg | wind turns by this much at the shift time |
| `wind_shift_t_frac`, `wind_shift_t_s` | –, s | shift time as a fraction of the horizon, and in seconds at the 60 min reference horizon |
| `md` | ratio | dead fuel moisture, every burnable class |
| `ign_win_x`, `ign_win_y` | – | ignition position in the 12.8 km reference window |

## Input tensor for the net

`initstates.TorchDataset(out, split, grid=None)[i]` returns `(x, row)` with `x` of shape
`(14, n, n)` float32, indexed `[channel, x, y]`, in physical units (normalise in training code):

| # | channel |
|---|---|
| 0 | burnable (0/1) |
| 1 | fuel depth e (m) |
| 2 | dead fuel load Sigmad (kg/m²) |
| 3 | surface-to-volume ratio sd (1/m) |
| 4 | altitude above the window minimum (m) |
| 5, 6 | terrain gradient dz/dx, dz/dy |
| 7, 8 | wind u, v before the shift (m/s, toward) |
| 9, 10 | wind u, v after the shift |
| 11 | shift time / horizon (constant plane) |
| 12 | dead fuel moisture (constant plane) |
| 13 | ignition mask (1 inside the initial burning area; a point is its one cell) |

Fuel goes in as physical properties instead of class ids, so a US fuel map with other classes uses
the same channels.

## Checked (cloud VM, ForeFire 2.6.0)

* 90 random samples ran through ForeFire with no failures.
* Edge hits (the fire reaches the window edge) occur only at high wind: 0% below 10 m/s, and
  14–21% at 15–20 m/s on the 12.8 km / 60 min window.
* Ellipse ignitions burn outward whichever way their nodes run, and all ignition cells are
  marked burned at t = 0. Early versus late 90° shifts give different fires (IoU 0.40).
* The existing `tests/test_sanity.py` still passes after the `sim.py` additions (`ign_polygon`,
  `wind_shift_t_s`).
* In 1–2% of samples, the ignition's 40 m cell is non-burnable even though its 10 m cell is
  burnable (a resampling edge case). Those fires may not spread.

## To swap in another landscape

Write a new config whose `landscape.path` is any ForeFire-format NetCDF (`fuel`, `altitude`,
`domain` with Lx/Ly), `fuel_table` is its ForeFire fuel CSV, and `nonburnable` lists its codes.
Set the holdout box for that map.
