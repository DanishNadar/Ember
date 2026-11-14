# Ember initial states v2.1: Corsica + six US sites (one mixed dataset)

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

**Changes in v2.1 (team decisions, Nov 14):**

* **Dead fuel moisture stays below extinction.** Each sample's 1-h moisture is rescaled to lie
  between the floor (0.02) and the extinction moisture of the fuel at its ignition point
  (`md_below_extinction`, US sites). No sample now starts in fuel that cannot burn (0 of 15,000 US
  rows, down from 46–66%). Fires can still die out when they reach wetter-extinction fuels next
  door, which is where the remaining no-spread cases come from. Corsica's extinction is 0.30 and
  its range already stops at 0.29, so it was already under the same rule.
* **Wind shift is ±60° and ramps.** The wind starts turning at `wind_shift_t_frac` × horizon
  and turns linearly over 30 min (`wind_shift_ramp_s` = 1800, as 60 s steps of uniform wind),
  like a frontal or sea-breeze passage. It used to jump instantly by up to ±180°.
* **Live fuel moisture is not sampled.** ForeFire's Corsica model (`Rothermel.cpp`) registers the
  live columns but never uses them, so live moisture can't vary in both regions. US runs use
  ForeFire's own defaults (live herb 0.70, live woody 1.00), and the live-moisture channels are
  gone. The live *load* channel stays, because it is a fuel property that Farsite uses.

* `all_samples.csv` holds every row, with `region` and `split` columns. Train on the mix. Use
  `region` only as metadata for evaluation.
* Corsica rows match `ember_init_v1` (same ignitions, windows, wind and moisture) except `wind_shift_deg`, which is rescaled from ±180° to ±60° with the same draw.
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
* **US moistures.** `md_10h = md + offset` and `md_100h = md_10h + offset`. Live moisture is fixed
  (see v2.1). Corsica's Rothermel reads only `md`.

## Input tensor: 19 channels, `[channel, x, y]`, physical units

Fuel goes in as physical properties, so the same channel value always means the same
vegetation, whatever the region's code system.

| # | channel | # | channel |
|---|---|---|---|
| 0 | burnable | 11, 12 | wind u, v after the shift (end of the ramp) |
| 1 | fuel depth (m) | 13 | shift start time / horizon |
| 2 | dead load (kg/m²) | 14 | md (1-h) |
| 3 | live load (kg/m²; 0 in Corsica) | 15 | md 10-h (0 in Corsica) |
| 4 | dead 1-h SAV (1/m) | 16 | md 100-h (0 in Corsica) |
| 5 | moisture of extinction | 17 | ignition mask |
| 6 | altitude above window min (m) | 18 | engine: 0 Corsica Rothermel, 1 Farsite |
| 7, 8 | dz/dx, dz/dy | | |
| 9, 10 | wind u, v before the shift (m/s, toward) | | |

The ramp length (1800 s) is the same for every sample and is stored in `meta.json`.

Read with `initstates.TorchDataset(out, "<region>/<split>")`. The layers are cropped from the
landscape on the fly.

**Why channel 18 exists:** the two regions are labelled by two different physics codes. ForeFire's
classic Rothermel skips mineral damping, which gives about 2.4× more reaction intensity. In the
smoke test, Corsica fires burn a median 2.7 km² in 1 h and US fires 0.16–0.36 km² (median per site). Without
the engine flag, a Corsica row and a US row with matching physical inputs would carry
contradictory labels. Ablate it if you want to know whether the net can tell the engines apart
on its own.

## Smoke test v2.1 (ForeFire 2.6.0, cloud VM, 80 random rows per region, 320 × 40 m, 60 min)

"No spread" = the burned area is at most 1.5× the ignition area plus 4 cells. The raw numbers are
in `smoke_v2.1.json` (next to this README).

| region (split) | failures | no spread | median burned | p90 burned | edge hits |
|---|---|---|---|---|---|
| corsica (train) | 0 | 7.5% | 2.67 km² | 43.1 km² | 15.0% |
| socal_chaparral (train) | 0 | 26.2% | 0.22 km² | 1.29 km² | 0% |
| norcal_paradise (train) | 0 | 25.0% | 0.16 km² | 1.42 km² | 0% |
| greatbasin_nv (train) | 0 | 20.0% | 0.31 km² | 2.07 km² | 0% |
| arizona (test_ood) | 0 | 26.2% | 0.33 km² | 1.57 km² | 0% |
| texas_panhandle (train) | 0 | 18.8% | 0.36 km² | 1.90 km² | 0% |
| montana_timber (train) | 0 | 32.5% | 0.32 km² | 1.55 km² | 0% |

**Corsica edge hits are 15%, and 26% at wind ≥ 10 m/s.** On the same 80 samples, the old
instant ±180° shift gave 12.5% (21% at ≥ 10 m/s), so the ramp adds only a little. The earlier
"2%" came from a 50-sample draw with fewer strong-wind runs and understated the problem. Edge-hit
labels are invalid, because ForeFire floods the outside of the domain. Either filter on
`edge_hit` or have the labeller use a bigger window for strong winds.

The schema columns and conventions are the same as in `ember_init_v1/README.md`, plus `region`, `group`,
`engine`, `fuel_source`, `md_10h`, `md_100h`, `m_live_herb`, `m_live_woody` (constant) and `mext_ignition` (US).
