"""Generate an isolated, monitorable Fuzzball v4 CPU+GPU overlap workflow.

Requires two already-uploaded archives:
  training input: output from orchestration/fuzzball/prepare_experiment.py,
  physics input: output from orchestration/observe/package_physics.py.

A single GPU run can coexist with two CPU-only ForeFire shards. Optional
second GPU experiment is independent hyperparameter training, NOT DDP.
"""
import argparse
from pathlib import Path
import re
import shlex

import yaml

GPU_IMAGE = "docker://nvcr.io/nvidia/pytorch:26.10-py3"


def volume(name, object_uri, result_uri):
    return {"use": "team15-scratch", "size": "20GiB",
            "ingress": [{"source": {"uri": object_uri},
                         "destination": {"uri": "file://input.tgz"}}],
            "egress": [{"source": {"uri": "file://results.tgz"},
                        "destination": {"uri": result_uri}}]}


def gpu_script(config, label):
    return f"""#!/bin/bash
set -euo pipefail
export EMBER_JOB=train-{label} OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1
tar -xzf /work/input.tgz -C /work
cd /work
python3 -c 'import torch; assert torch.cuda.is_available(); print("CUDA", torch.cuda.get_device_name(0), flush=True)'
# Matplotlib is needed for genuine held-out prediction maps.
python3 -c 'import matplotlib' || python3 -m pip install --no-input 'matplotlib>=3.7,<4'
python3 -m pip freeze > /work/pilot/{label}_environment.txt
python3 -u orchestration/fuzzball/execute_training.py train --config /work/pilot/{config}.yaml 2>&1 | tee /work/pilot/{label}_workflow.log
python3 -u orchestration/fuzzball/execute_training.py evaluate --config /work/pilot/{config}.yaml 2>&1 | tee -a /work/pilot/{label}_workflow.log
tar -czf /work/results.tgz -C /work pilot/outputs_{config} pilot/{config}.yaml pilot/dataset_manifest.json pilot/package_manifest.json pilot/{label}_workflow.log pilot/{label}_environment.txt
"""


def cpu_script(index, shards, workers, per_region):
    return f"""#!/bin/bash
set -euo pipefail
export EMBER_JOB=physics-{index} OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1
tar -xzf /work/input.tgz -C /work
cd /work
# Published ForeFire 2.6 Linux aarch64 wheel is CPU-only.
python3 -m pip install --no-input 'forefire==2.6.0' 'netCDF4>=1.7,<2' 'psutil>=6,<8'
python3 -u orchestration/observe/cpu_shard.py --source /work/dataset/ember_init_v2 --shard {index} --shards {shards} --workers {workers} --per-region {per_region} --output /work/output 2>&1 | tee /work/physics_workflow.log
tar -czf /work/results.tgz -C /work output physics_workflow.log
"""


def make_workflow(training_uri, physics_uri, result_prefix, *, workers=16, per_region=80,
                  parallel_gpu=True, image=GPU_IMAGE):
    if not result_prefix.startswith("fb://user/") or result_prefix.endswith("/"):
        raise ValueError("result_prefix must be fb://user/... without trailing slash")
    if not training_uri.startswith("fb://") or not physics_uri.startswith("fb://"):
        raise ValueError("Use uploaded Fuzzball object URIs for inputs")
    if not (1 <= workers <= 16) or per_region <= 0:
        raise ValueError("workers must be 1..16 and per_region > 0")
    volumes, jobs = {}, {}
    for index in range(2):
        key = f"physics-{index}"
        vol = key + "-data"
        volumes[vol] = volume(vol, physics_uri, result_prefix + f"/{key}-results.tgz")
        jobs[key] = {
            "image": {"uri": image}, "mounts": {"/work": vol},
            "resource": {"cpu": {"cores": workers}, "memory": {"size": "40GiB"}},
            "script": cpu_script(index, 2, workers, per_region)}
    experiments = [("baseline", "baseline")]
    if parallel_gpu:
        experiments.append(("lower-lr", "lower_lr"))
    for job_name, config in experiments:
        key = "train-" + job_name
        vol = key + "-data"
        volumes[vol] = volume(vol, training_uri, result_prefix + f"/{key}-results.tgz")
        jobs[key] = {
            "image": {"uri": image}, "mounts": {"/work": vol},
            "resource": {"cpu": {"cores": 4}, "memory": {"size": "16GiB"},
                         "devices": {"nvidia.com/gpu": 1}},
            "script": gpu_script(config, job_name)}
    for job in jobs.values():
        job["script"] = job["script"].replace("set -euo pipefail\n", "set -euo pipefail\nexport EMBER_EXPERIMENT_ID="
                                            + shlex.quote(result_prefix) + "\n", 1)
    # Deliberately no depends-on: independent CPU and GPU jobs overlap when scheduled.
    return {"version": "v4", "volumes": volumes, "jobs": jobs}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--training-uri", required=True)
    p.add_argument("--physics-uri", required=True)
    p.add_argument("--result-prefix", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cpu-workers", type=int, default=16)
    p.add_argument("--scenarios-per-region", type=int, default=80)
    p.add_argument("--one-gpu", action="store_true", help="Train baseline only (CPU shards still parallel)")
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing Fuzzfile: {a.output}")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    wf = make_workflow(a.training_uri, a.physics_uri, a.result_prefix,
                       workers=a.cpu_workers, per_region=a.scenarios_per_region,
                       parallel_gpu=not a.one_gpu)
    a.output.write_text(yaml.safe_dump(wf, sort_keys=False), encoding="utf-8")
    print(f"Fuzzfile created: {a.output}")
    print("Jobs:", ", ".join(wf["jobs"]))
    print("Validate with fuzzball workflow validate, then submit. Execution not claimed.")


if __name__ == "__main__":
    main()
