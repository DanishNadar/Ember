# Ember data extraction

## Implemented workflow

1. `scripts/run_forefire.py` runs a supplied CLI executable, measures wall time/RSS, and writes a manifest. If the executable is unavailable, it writes a blocked record rather than synthetic results.
2. `scripts/extract_state.py` copies an immutable raw KML or GeoJSON state into `artifacts/raw/<scenario>/`, parses polygons, writes normalized GeoJSON plus a binary raster mask to `artifacts/processed/<scenario>/`, and atomically publishes a SHA-256 provenance manifest.
3. `scripts/extract_environment.py` inspects an HDF5-backed NetCDF landscape and samples recognized `fuel`, `altitude`, and `wind` arrays onto the state grid using its `BBoxWSEN` extent. It retains all wind leading axes.
4. `scripts/build_dataset.py` creates next-state samples only from ordered states carrying `valid_at`. It assigns entire scenario identifiers—not individual time steps—to deterministic train/validation/test splits.

## Verified extraction artifact

Input: `forefire/tests/runff/real_case.kml.ref` (12,661 bytes, SHA-256 `b3d483a73911521aaf1eeca7005dcf8ef093a00176ecf16938c88be2ef3dec89`). This is a checked-in reference artifact, not a newly generated ForeFire run.

| Output | Location | Result |
|---|---|---|
| Raw immutable copy | `artifacts/raw/forefire_runff_reference/real_case.kml.ref` | Preserved |
| Processed geometry | `artifacts/processed/forefire_runff_reference/front.geojson` | 1 polygon, 637 vertices |
| Common raster | `artifacts/processed/forefire_runff_reference/state.npz` | 256×256 binary mask; 36,132 occupied cells |
| Environment arrays | `artifacts/processed/forefire_runff_reference/environment.npz` | aligned fuel, altitude, and all stored wind slices |
| Provenance/validation | `artifacts/manifests/forefire_runff_reference.json` | Complete with source hash, config, runtime versions, and caveats |

An additional arrival-time extractor processes `ForeFire.0.nc.ref` into `artifacts/processed/forefire_runff_arrival_reference/arrival_time.npz` with a separate provenance record at `artifacts/arrival/forefire_runff_arrival_reference.json`.

## Integrity and resume behavior

Extraction validates a two-dimensional binary mask and nonempty geometry. Published JSON manifests are written atomically. `--resume` returns an already complete scenario manifest rather than overwriting derived outputs. A unit test verifies both the geometry calculation and this resume behavior.

## Dataset status

`artifacts/datasets/dataset_manifest.json` records a deliberately blocked dataset: the single KML state supplies neither `valid_at` nor a successor state, so it cannot form an `X_t -> Y_(t+delta)` label. This avoids falsely treating spatial resampling of one state as training data.

## Alignment caveat

The environment sampler uses nearest-neighbour BBoxWSEN mapping. The stored row-axis is provisionally treated as south-to-north, and the KML reference lacks a timestamp. Both spatial orientation and wind-time selection must be validated against a locally generated ForeFire state before using the arrays for quantitative model training.
