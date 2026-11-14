# Ember initial-state dataset (`ember_init_v2`)

> **Inputs only.** These are 26,000 fire *starts* (landscape crop, ignition, wind, moisture).
> There are **no ForeFire labels yet**: arrival-time / burned-area targets come later from the
> labelling pipeline, which runs ForeFire on `ember_init_v2/all_samples.csv`.

## What is here

| path | what |
|---|---|
| `ember_init_v2/` | the dataset: `all_samples.csv` (every row, with `region` and `split`), plus `<region>/<split>/{samples.csv,meta.json}`. Full description, 21-channel tensor spec, evaluation protocol and known caveats in [`ember_init_v2/README.md`](ember_init_v2/README.md). |
| `configs/init_v2.json` | the exact config that built v2 (`init_corsica.json` = Corsica-only v1). |
| `ember_bench/` | generator + ForeFire wrapper (`initstates.py`, `sim.py`, `us_landscape.py`, `landfire.py`, …). |
| `data_real/aullene/data.nc` | ForeFire's real Aullène (Corsica) landscape, 3.9 MB. |
| `data_real/us/<site>.npz` | the six US landscapes (AWS Terrain Tiles 30 m DEM + LANDFIRE fuel on the same grid). |
| `data_real/us/landfire/*_LF2025_FBFM40.tif` | raw LANDFIRE LF2025 FBFM40 tiles (EPSG:5070) the `.npz` fuel was reprojected from. |
| `tests/` | `test_orientation.py` (terrain axis fix) and `test_sanity.py`. |
| `ember_init_v1/README.md` | base column schema/conventions that v2 extends. |

| region | engine | train | val | test | test_ood |
|---|---|---|---|---|---|
| corsica | ForeFire `Rothermel` (CORSICA_NATIVE) | 10,000 | 1,000 | 1,000 | 1,000 |
| socal_chaparral, norcal_paradise, greatbasin_nv, texas_panhandle, montana_timber | ForeFire `Farsite` | 2,000 each | 200 each | 200 each | – |
| arizona (held-out site) | ForeFire `Farsite` | – | – | – | 1,000 |

`region` / `group` are evaluation metadata only. Train on the mix.

## ForeFire scenarios (for labelling)

`scenarios.jsonl` is not committed: it is a pure function of `samples.csv` + the config in `meta.json`
(~100 MB, and a built copy hardcodes absolute landscape paths). Get the ForeFire-ready scenario dicts with

```python
from ember_bench.initstates import scenarios_for
scs = scenarios_for("ember_init_v2", "texas_panhandle/train")   # list of sim.run_scenario() dicts
```

which resolves `data_real/` against this checkout. Verified identical (apart from the path) to the
original jsonl for all 26,000 rows.

## Rebuild / check

All paths are relative to this `dataset/` folder.

```bash
cd dataset
pip install forefire numpy          # ForeFire 2.6.0 wheels (x86_64 + aarch64)
python -m ember_bench.initstates check --config configs/init_v2.json --out ember_init_v2
python -m ember_bench.initstates smoke --config configs/init_v2.json --out ember_init_v2   # runs a few rows through ForeFire
python -m ember_bench.initstates build --config configs/init_v2.json --out ember_init_v2   # regenerates everything
```

Load samples as tensors with `ember_bench.initstates.TorchDataset("ember_init_v2", "<region>/<split>")`;
layers are cropped from `data_real/` on the fly, so keep the folder layout as is.

## Known caveats (team decisions pending)

* **US moisture:** 46–66% of US samples start with 1-h moisture above the ignition fuel's
  moisture of extinction, so they barely spread. Narrow the `md` range or keep them as no-spread cases.
* **Farsite downslope bug:** ForeFire's Farsite model still spreads downslope about as fast as upslope.
* **Terrain variety** is limited (about 8 independent 12.8 km windows in Corsica, about 41 across US train sites).
