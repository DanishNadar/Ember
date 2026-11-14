# ⚡ Ember Lab 01 — Fuzzball dependency handoff

**Scope:** First of three cluster-computing experiments. Demonstrates a new,
independent training experiment becoming eligible for scheduling as soon as the
simulation stage completes. This does *not* copy a running model, change a
running job's resources, or provide PyTorch DDP/elastic scaling.

## Local dependency smoke test

From repository root:

```bash
python orchestration/handoff/smoke_test.py
```

The smoke test uses artificial sleep commands **only to verify dependency
ordering**. It launches simulator and baseline jobs concurrently, waits for
simulation success, starts a secondary job, and checks ordering. It cannot
establish real accelerator utilization or any model-training speedup.

For real local commands, create your own JSON config file in a directory
that holds your run inputs (not checked into Git):

```json
{
  "output_dir": "handoff_results_01",
  "simulate": ["python", "/absolute/path/to/actual_simulator_runner.py"],
  "baseline": ["python", "/absolute/path/to/Ember/ml/train.py", "--config", "/absolute/path/to/Ember/ml/baseline.yaml"],
  "secondary": ["python", "/absolute/path/to/Ember/ml/train.py", "--config", "/absolute/path/to/Ember/ml/secondary.yaml"]
}
```

Then:

```bash
python orchestration/handoff/run_local.py --config /path/to/run.json
```

The commands run with CWD set to the JSON config's directory.
`events.json` records true wall-clock *job event ordering*, individual logs,
failures and total wall-clock duration. The three commands must be real and
separately tested. The simulator must exit successfully and should persist its
outputs before the secondary job starts. Ensure baseline and secondary configs
point to **different output directories**; the existing Ember `ml/train.py`
refuses to overwrite a nonempty output directory. The baseline starts alongside
the simulation, so it needs a ready dataset; this is not live streaming.

## Fuzzball workflow (cluster integration template)

`fuzzfile.example.yaml` expresses the same job DAG using Fuzzball v4
`depends-on: status: FINISHED`. Before using it:

1. Build/publish correct ARM64 OCI images with validated simulator and ML
   dependencies, replacing the two registry/tag placeholders.
2. Replace the sample simulator command with the *actual* entrypoint (the
   repository has not established that `/app/sim/run_shard.py` exists).
3. Stage a real, leakage-safe dataset and baseline/secondary config in the
   mounted shared volume. Use **distinct** output directories and learning
   rates/hyperparameters.
4. Verify Fuzzball cluster GPU/CPU quotas and the persistent volume
   `ember-data`; confirm whether images and /app paths match.
5. Submit via the team's working Fuzzball CLI/MCP, inspect actual workflow
   start/finish times, logs and node placement, then benchmark the fixed
   schedule versus handoff. No claims of speedup until independently measured.

**Important physical caveat:** ForeFire is mostly CPU-based. Ending a CPU-only
simulator job does not necessarily release an idle GPU! The second GPU
experiment uses an *available* GPU that Fuzzball allocates when the job can
start. A true “free GPU reallocation” demo requires a workload/resource
topology that actually frees GPU capacity.

## Next alternatives

- **Lab 02 (DDP):** one checkpointed model restarted across two GPUs, with
  synchronized gradients; not implemented here.
- **Lab 03 (elastic):** live changing worker membership with reliable restart
  semantics, subject to cluster and framework capability; not implemented here.

## Metrics

The local events JSON can confirm scheduling order. It does **not** measure
CUDA kernel activity, GPU utilization, node placement or training
quality. Collect those separately from Fuzzball/GPU logs. Do not display
the local sleep timings as a performance benchmark.
