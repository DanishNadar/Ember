# Ember

Ember is a reproducible extraction and analysis layer around the vendored ForeFire source checkout. It does not rename, fork, or replace the ForeFire engine. Install the local analysis dependencies with `python -m pip install -r requirements.txt`.

## Surrogate dataset

The ForeFire initial-state dataset for the neural surrogate (26k fire starts, Corsica + six US LANDFIRE sites, inputs only, labels pending) and the code that rebuilds it live in [`dataset/`](dataset/README.md).

## Current verified workflow

The original extraction smoke test processes a checked-in KML reference without presenting it as a new simulation result:

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

## Development and verified experiments

Use the canonical `HPC_Hacks/Ember` checkout and the workflow in
[DEVELOPMENT.md](DEVELOPMENT.md). The [verified Fuzzball pilot](orchestration/fuzzball/RESULTS.md)
trained and evaluated the direct-arrival model on 144 genuine ForeFire simulations.
The [Observatory notebook](notebooks/Ember_Observatory.ipynb) replays saved results
and can explicitly monitor jobs. Use `python scripts/export_observatory.py` to
create a versioned local report; publishing requires a separate approved action.

### Two-Node Distributed Fine-Tuning — November 15, 2026

Project Ember successfully executed synchronized PyTorch DistributedDataParallel fine-tuning across two NVIDIA GB10 GPUs on separate nodes, orchestrated by Fuzzball v4 with OpenMPI and NCCL.

The experiment used a 19-channel U-Net wildfire arrival-time model initialized from a pretrained checkpoint. A dataset of 3,000 ForeFire simulations was staged on shared NFS storage. Training used one process per GPU, distributed sampling, synchronized gradients, and rank-zero checkpointing.

**Configuration:** 2 nodes, 2 GPUs, batch size 2 per rank, learning rate 0.0001, one fine-tuning epoch.

**Validation results:** Loss 0.03390, IoU 0.3668, Dice 0.5367, precision 86.93%, recall 38.82%, and arrival-time MAE 498.27 seconds.

**Execution:** Training took 142.3 seconds, with 13.4 seconds for validation. Both ranks exited successfully, and the resulting checkpoint was exported through Fuzzball object storage.

This run demonstrates functional multi-node GPU training. It does not establish performance improvement over the pretrained baseline or independent test-set generalization. The pretrained checkpoint does not contain historical split identities, so historical held-out status remains unverified.
