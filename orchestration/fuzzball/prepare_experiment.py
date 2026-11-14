"""Package verified pilot data and emit bounded one/two-GPU Fuzzfiles."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
IMAGE = "docker://nvcr.io/nvidia/pytorch:26.10-py3"
IMAGE_INDEX = "sha256:6d347d649d5dd108b4652f1b9cea6a3c859692ac408617a9108616da40e3da1f"
IMAGE_ARM64 = "sha256:c24a66e7694a2ffc04851fba93ada27f09066c49e0779242660372e5f023a7c0"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def workflow(prefix, jobs):
    volumes, definitions = {}, {}
    for name, config, evaluate in jobs:
        script = f"""#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONUNBUFFERED=1
tar -xzf /work/input.tgz -C /work
cd /work
python3 -c 'import torch, numpy, yaml; print(torch.__version__)'
python3 -m pip freeze > /work/pilot/{name}_environment.txt
python3 orchestration/fuzzball/execute_training.py train --config /work/pilot/{config}.yaml 2>&1 | tee /work/pilot/{name}_workflow.log
"""
        if evaluate:
            script += f"python3 orchestration/fuzzball/execute_training.py evaluate --config /work/pilot/{config}.yaml 2>&1 | tee -a /work/pilot/{name}_workflow.log\n"
        script += f"tar -czf /work/results.tgz -C /work pilot/outputs_{config} pilot/{config}.yaml pilot/dataset_manifest.json pilot/package_manifest.json pilot/{name}_workflow.log pilot/{name}_environment.txt\n"
        volume = name + "-data"
        volumes[volume] = {"use": "team15-scratch", "size": "20GiB",
                         "ingress": [{"source": {"uri": f"fb://user/ember/{prefix}/input.tgz"},
                                      "destination": {"uri": "file://input.tgz"}}],
                         "egress": [{"source": {"uri": "file://results.tgz"},
                                     "destination": {"uri": f"fb://user/ember/{prefix}/{name}-results.tgz"}}]}
        definitions[name] = {"image": {"uri": IMAGE}, "mounts": {"/work": volume},
                             "resource": {"cpu": {"cores": 4}, "memory": {"size": "16GiB"},
                                          "devices": {"nvidia.com/gpu": 1}}, "script": script}
    return {"version": "v4", "volumes": volumes, "jobs": definitions}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--prefix", required=True)
    a = p.parse_args()
    data = a.dataset.resolve()
    manifest = json.loads((data / "dataset_manifest.json").read_text())
    assert manifest["status"] == "complete"
    families, ids, counts = {}, {}, {}
    for split in ("train", "val", "test"):
        counts[split] = 0
        for file in sorted((data / "data" / split).glob("*.npz")):
            with np.load(file, allow_pickle=False) as z:
                assert z["x"].shape == (19, 320, 320) and z["x"].dtype == np.float32
                assert z["arrival_time_seconds"].dtype == np.float32
                assert z["channel_names"].tolist() == manifest["channel_names"]
                for mapping, key in ((families, "scenario_family_id"), (ids, "simulation_id")):
                    value = z[key].item()
                    assert value not in mapping or mapping[value] == split, f"Split leakage: {value}"
                    mapping[value] = split
            counts[split] += 1
    assert counts == manifest["sample_counts"] == {"train": 96, "val": 24, "test": 24}
    for record in manifest["simulations"]:
        if record["accepted"]:
            assert sha(data / record["file"]) == record["sha256"]
    base = yaml.safe_load((data / "baseline.yaml").read_text())
    (data / "initial.yaml").write_text(yaml.safe_dump(dict(base, output_dir="outputs_initial"), sort_keys=False))
    members = {}
    for file in (ROOT / "ml").iterdir():
        if file.suffix in {".py", ".yaml", ".txt"}:
            members["ml/" + file.name] = file
    members["orchestration/fuzzball/execute_training.py"] = HERE / "execute_training.py"
    for file in (data / "data").rglob("*.npz"):
        members["pilot/" + file.relative_to(data).as_posix()] = file
    for name in ("dataset_manifest.json", "initial.yaml", "baseline.yaml", "lower_lr.yaml"):
        members["pilot/" + name] = data / name
    package_manifest = {"sha256": {name: sha(file) for name, file in members.items()},
                        "image": IMAGE, "registry_index_digest": IMAGE_INDEX,
                        "registry_arm64_digest": IMAGE_ARM64,
                        "sample_counts": counts, "scenario_families": families}
    (data / "package_manifest.json").write_text(json.dumps(package_manifest, indent=2))
    members["pilot/package_manifest.json"] = data / "package_manifest.json"
    packages = HERE / "packages"
    packages.mkdir(exist_ok=True)
    archive = packages / (a.prefix + "-input.tgz")
    with archive.open("xb") as raw:
        with tarfile.open(fileobj=raw, mode="w:gz") as tar:
            for name, file in members.items():
                tar.add(file, arcname=name, recursive=False)
    for name, jobs in (("initial", [("initial", "initial", True)]),
                       ("parallel", [("baseline", "baseline", True), ("lower-lr", "lower_lr", True)])):
        file = HERE / (a.prefix + "-" + name + ".fz")
        with file.open("x") as handle:
            yaml.safe_dump(workflow(a.prefix, jobs), handle, sort_keys=False)
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size,
                      "sha256": sha(archive), "members": len(members), "sample_counts": counts,
                      "input_uri": f"fb://user/ember/{a.prefix}/input.tgz"}, indent=2))


if __name__ == "__main__":
    main()
