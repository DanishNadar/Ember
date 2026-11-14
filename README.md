# Ember

Ember is a reproducible extraction and analysis layer around the vendored ForeFire source checkout. It does not rename, fork, or replace the ForeFire engine. Install the local analysis dependencies with `python -m pip install -r requirements.txt`.

## Current verified workflow

The local host cannot currently build or run ForeFire, so the checked-in KML reference artifact can be processed without presenting it as a new simulation result:

```powershell
python scripts/extract_state.py forefire/tests/runff/real_case.kml.ref --scenario-id forefire_runff_reference --grid 256
python scripts/analyze_scenario.py artifacts/manifests/forefire_runff_reference.json
python scripts/extract_arrival_time.py forefire/tests/runff/ForeFire.0.nc.ref --artifact-id forefire_runff_arrival_reference
python scripts/create_visuals.py
python scripts/build_dataset.py artifacts/manifests
python -m unittest discover -s tests -v
```

Raw inputs are copied to `artifacts/raw/<scenario-id>/`; derived GeoJSON and compressed masks go under `artifacts/processed/<scenario-id>/`; each run has an atomic manifest in `artifacts/manifests/`.

To run a supported installed engine and retain real runtime/RSS measurements:

```powershell
python scripts/run_forefire.py forefire/tests/runff/real_case.ff --run-directory artifacts/runs/runff --executable forefire
```

The runner writes a blocked manifest instead of substituting synthetic timings when the executable is absent. See `reports/` for observed limitations and the required environment setup.

When real completed CLI manifests exist, create a performance chart with `python scripts/plot_performance.py`. The command intentionally exits with an explanation rather than charting blocked or missing measurements.
