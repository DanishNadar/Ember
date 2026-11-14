# Exploratory analysis of the available ForeFire reference artifact

## Scope

This analysis covers one checked-in KML front reference plus its matching landscape fixture. It is a data inspection, not a simulation-performance experiment or validation against an observed wildfire.

## Spatial results

| Measurement | Observed value | Interpretation limit |
|---|---:|---|
| Polygon count | 1 | One exported front polygon. |
| Vertex count | 637 | Geometry complexity of this artifact only. |
| Bounding box | `[8.78649, 41.96646, 8.80824, 41.97348]` | Longitude/latitude-looking coordinates, but CRS is absent from the KML. |
| Polygon area | `8.41703998162302e-05` source-coordinate² | Do not interpret as square metres. |
| Polygon perimeter | `0.0938002008428497` source-coordinate units | Do not interpret as metres. |
| 256×256 mask occupancy | 0.55133056640625 | Depends on analysis-grid resolution and bounding-box extent. |

## Environmental fields in the aligned 256×256 window

| Field | Observed range | Mean | Notes |
|---|---:|---:|---|
| Fuel index | 62–121 | 94.677978515625 | Ten sampled indices; index 102 occupies 32,396 grid cells. |
| Altitude (native value) | 55–115 | 89.21504211425781 | Units absent from fixture metadata. |
| Wind (all retained values) | 0.0164177399–1.0454379320 | 0.5159910917 | Shape is 2×2×256×256; leading-axis meaning/time alignment unverified. |

No missing values were found in the binary mask or the sampled environmental arrays. The result does not establish relationships between fuel, terrain, wind, and spread because there is only one untimestamped front and no independent outcome series.

## Arrival-time reference output

The separately stored `ForeFire.0.nc.ref` output has a 3200×3200 arrival-time grid over a 64,000×64,000 model-coordinate domain. With its observed `-9999` sentinel excluded, 1,460 of 10,240,000 cells are valid; their values range from 32.3334515372 to 2399.2142331354 seconds (mean 1782.1609139565 seconds). The active region is visualized at `artifacts/figures/forefire_runff_arrival_reference_arrival_time.png`. This is still a checked-in reference output, not a local run; it must not be used as a runtime measurement or claimed as a new result.

## Figures and numerical records

- `artifacts/figures/forefire_runff_reference_front_and_mask.png`
- `artifacts/figures/forefire_runff_reference_environment.png`
- `artifacts/figures/forefire_runff_reference_landscape_front.png`
- `artifacts/figures/forefire_runff_reference_fuel_composition.png`
- `artifacts/figures/forefire_runff_reference_arrival_story.png`
- `artifacts/figures/forefire_runff_arrival_reference_arrival_time.png`
- `artifacts/analysis/forefire_runff_reference.json`

## Analyses not possible from current evidence

Temporal area/perimeter growth, front displacement, numerical stability, step sensitivity, duplicate trajectories, simulator runtime, resource utilization, model accuracy, uncertainty calibration, and causal environmental effects all require timestamped outputs from actual completed ForeFire runs. Those are intentionally not estimated here.
