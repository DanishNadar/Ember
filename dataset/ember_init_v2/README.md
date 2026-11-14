# Ember initial states v2: Corsica + six US sites (one mixed dataset)

26,000 fire starts (inputs only, no ForeFire labels yet), built by
`python -m ember_bench.initstates build --config configs/init_v2.json --out ember_init_v2`.

| group / region | landscape | ForeFire engine | train | val | test | test_ood (unseen terrain) |
|---|---|---|---|---|---|---|
| france / `corsica` | ForeFire's real Aullène data.nc (real fuel + terrain), 64 km | classic `Rothermel`, CORSICA_NATIVE | 10,000 | 1,000 | 1,000 | 1,000 (southern 16 km strip) |
| us / `socal_chaparral` | 33.85–34.35 N, 119.10–118.50 W | `Farsite` + STDfarsiteFuelsTable | 2,000 | 200 | 200 | – |
| us / `norcal_paradise` | 39.55–40.05 N, 121.85–121.25 W | Farsite | 2,000 | 200 | 200 | – |
| us / `greatbasin_nv` | 40.65–41.15 N, 117.15–116.55 W | Farsite | 2,000 | 200 | 200 | – |
| us / `texas_panhandle` | 35.55–36.05 N, 100.95–100.35 W | Farsite | 2,000 | 200 | 200 | – |
| us / `montana_timber` | 46.55–47.05 N, 114.35–113.75 W | Farsite | 2,000 | 200 | 200 | – |
| us / `arizona` | 34.05–34.55 N, 111.55–110.95 W | Farsite | – | – | – | 1,000 (whole site never trained on) |

US sites: real terrain from AWS Terrain Tiles at 30 m (each box is about 46–55 × 56 km).
**US fuel is real LANDFIRE LF2025 FBFM40** at 30 m (`data_real/us/landfire/<site>_LF2025_FBFM40.tif`,
EPSG:5070), reprojected onto the terrain grid. Each tile covers its whole box (at most 0.01% of
land cells missing, which are set non-burnable). LANDFIRE water matches the DEM coastline at IoU
0.90 in SoCal, against 0.002 when flipped. Codes 91–93 (urban, snow, agriculture) become
non-burnable 99. Which US site is held out is set in `configs/init_v2.json`, and the team
chooses it.

| site | burnable | main fuels (LF2025) |
|---|---|---|
| socal_chaparral | 43% (39% is sea, 18% urban) | GS2 14%, GR2 7%, SH2 6%, SH5 5% |
| norcal_paradise | 91% | TU5 19%, GR2 16%, SH4 7%, TL3 7% |
| greatbasin_nv | 97% | GR2 54%, GS2 23%, GR1 7%, GS1 6% |
| arizona (held out) | 96% | GS2 36%, TL8 20%, GR2 14%, TL3 10% |
| texas_panhandle | 93% | GR2 42%, GR1 41%, GS2 5% |
| montana_timber | 92% | GS2 17%, TU2 16%, TU5 12%, SH2 12% |

**Moisture warning (measured; the team decides):** the US 1-h moisture range is 0.02–0.40, but
most US fuels go out at 12–25% moisture of extinction. As a result, **46–66% of US samples per
site start above the extinction moisture of the fuel at the ignition point**, so they barely
spread or don't spread at all. In Corsica the share is 0%. Narrowing the US `md` range in the
config, or keeping these samples as "no-spread" cases, is a team call.

* `all_samples.csv` holds every row, with `region` and `split` columns. Train on the mix. Use
  `region` only as metadata for evaluation.
* Corsica rows are identical to `ember_init_v1`, apart from the `corsica-` prefix on `sample_id`.
* `group` (france / us) and `region` (the site) are metadata for evaluation only. They are not
  inputs to the net.

## Evaluation protocol

1. **Mixed:** train on both `train` splits, then report `test` and `test_ood` per region.
2. **Unseen US site:** `arizona/test_ood` is never trained on.
3. **Cross-country:** train on one group, then test on the other. This answers "does it work
   somewhere it has never seen?"

## Uniqueness and terrain variety (measured)

* All 26,000 parameter tuples are unique, and 25,718 ignitions fall in distinct 40 m cells.
* Terrain is **not** 10,000 different landscapes. At most about 8 non-overlapping 12.8 km
  windows fit in Corsica train. Each 0.5° × 0.6° US box holds about 7–9, which makes
  about 41 independent windows across the five US train sites, plus about 8 in held-out Arizona.
  Beyond that, variety comes from ignition location, weather and moisture.

## Changes in v2

* **Terrain orientation fix (`sim.py`).** pyforefire reads the altitude layer with axis 0 = y.
  Every run before this fix had its terrain mirrored across the diagonal. `tests/test_orientation.py`
  guards the fix.
* **US engine.** `fuel_set="farsite"`. Fuel codes are FBFM40 codes. On flat ground, head ROS
  matches BehavePlus: SH5 at 10 m/s 20-ft wind gives 36.8 m/min against a reference of 37.6. The
  sim works around two Farsite bugs: it passes wind in mph, and it halves the altitude layer
  because Farsite doubles tan(slope). **Still wrong:** Farsite spreads downslope as fast as
  upslope (checked: 380 m down vs 360 m up). Fixing that needs a source patch.
* **US moistures.** `md_10h = md + offset`, `md_100h = md_10h + offset`, and live herb and live
  woody are sampled. All are in the config. Corsica's Rothermel reads only `md`.

## Input tensor: 21 channels, `[channel, x, y]`, physical units

Fuel goes in as physical properties, so the same channel value always means the same
vegetation, whatever the region's code system.

| # | channel | # | channel |
|---|---|---|---|
| 0 | burnable | 11, 12 | wind u, v after the shift |
| 1 | fuel depth (m) | 13 | shift time / horizon |
| 2 | dead load (kg/m²) | 14 | md (1-h) |
| 3 | live load (kg/m²; 0 in Corsica) | 15 | md 10-h (0 in Corsica) |
| 4 | dead 1-h SAV (1/m) | 16 | md 100-h (0 in Corsica) |
| 5 | moisture of extinction | 17 | live herb moisture (0 in Corsica) |
| 6 | altitude above window min (m) | 18 | live woody moisture (0 in Corsica) |
| 7, 8 | dz/dx, dz/dy | 19 | ignition mask |
| 9, 10 | wind u, v before the shift (m/s, toward) | 20 | engine: 0 Corsica Rothermel, 1 Farsite |

Read with `initstates.TorchDataset(out, "<region>/<split>")`. The layers are cropped from the
landscape on the fly.

**Why channel 20 exists:** the two regions are labelled by two different physics codes. ForeFire's
classic Rothermel skips mineral damping, which gives about 2.4× more reaction intensity. In the
smoke test, Corsica fires burn a median 2.5 km² in 1 h and US fires 0.07–0.21 km² (median per site). Without
the engine flag, a Corsica row and a US row with matching physical inputs would carry
contradictory labels. Ablate it if you want to know whether the net can tell the engines apart
on its own.

## Smoke test (ForeFire 2.6.0, cloud VM, 50 random rows per set, 320 × 40 m, 60 min)

| set | failures | median burned | edge hits |
|---|---|---|---|
| corsica/train | 0 | 2.47 km² | 2% (all at 15–20 m/s) |
| corsica/test_ood | 0 | 2.05 km² | 2% |
| US sites (30 each, LANDFIRE fuel) | 0 | 0.07–0.21 km² | 0% |

The schema columns and conventions are the same as in `ember_init_v1/README.md`, plus `region`, `group`,
`engine`, `fuel_source`, `md_10h`, `md_100h`, `m_live_herb` and `m_live_woody`.
