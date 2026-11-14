"""Run the existing arrival CLI and collect measured hardware/timing/artifacts."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from train_arrival import config_from
from arrival_dataset import load_pair
from arrival_model import ArrivalUNet


def hardware():
    assert platform.machine() in {"aarch64", "arm64"}, "ARM64 container required"
    assert torch.cuda.is_available(), "CUDA unavailable; refusing CPU fallback"
    p = torch.cuda.get_device_properties(0)
    # Execute a CUDA kernel before claiming CUDA works.
    a = torch.arange(1024, device="cuda", dtype=torch.float32)
    assert float((a * 2).sum()) == 1047552.0
    torch.cuda.synchronize()
    smi = subprocess.run(["nvidia-smi"], text=True, capture_output=True)
    return {"hostname": socket.gethostname(), "architecture": platform.machine(),
            "python": sys.version, "torch": torch.__version__, "cuda": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(), "gpu_name": p.name,
            "device_count": torch.cuda.device_count(), "device_memory_bytes": p.total_memory,
            "compute_capability": [p.major, p.minor], "cuda_kernel_verified": True,
            "nvidia_smi": smi.stdout, "nvidia_smi_error": smi.stderr}


def latency(checkpoint, cfg):
    net = ArrivalUNet(len(cfg["channel_names"]), cfg["base_filters"], cfg["depth"], cfg["dropout"]).cuda()
    net.load_state_dict(checkpoint["model_state_dict"])
    net.eval()
    sample = sorted((Path(cfg["data_dir"]) / "test").glob("*.npz"))[0]
    x = load_pair(sample, cfg)[0]
    norm = checkpoint["normalization"]
    x = (x - np.asarray(norm["mean"], dtype=np.float32)[:, None, None]) / np.asarray(norm["std"], dtype=np.float32)[:, None, None]
    x = torch.from_numpy(x[None].astype(np.float32)).cuda()
    timings = []
    with torch.inference_mode():
        for _ in range(5):
            net(x)
        torch.cuda.synchronize()
        for _ in range(30):
            start = time.perf_counter()
            net(x)
            torch.cuda.synchronize()
            timings.append((time.perf_counter() - start) * 1000)
    return {"batch_size": 1, "warmup_steps": 5, "repeats": 30,
            "mean_ms": float(np.mean(timings)), "median_ms": float(np.median(timings)),
            "scope": "resident-input CUDA forward only; excludes preprocessing, transfers and output writing"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["train", "evaluate"])
    p.add_argument("--config", type=Path, required=True)
    args = p.parse_args()
    package = ROOT / "pilot/package_manifest.json"
    for member, expected in json.loads(package.read_text())["sha256"].items():
        if hashlib.sha256((ROOT / member).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Staged file checksum differs: {member}")
    cfg = config_from(args.config)
    out = Path(cfg["output_dir"])
    hw = hardware()
    print("HARDWARE " + json.dumps(hw), flush=True)
    checkpoint_path = out / "best.pt"
    if args.mode == "train":
        command = [sys.executable, "-u", str(ROOT / "ml/train_arrival.py"), "train", "--config", str(args.config)]
        t0 = time.perf_counter()
        process = subprocess.Popen(command, cwd=ROOT / "ml", stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        lines, reported = [], False
        for line in process.stdout:
            print(line, end="", flush=True)
            lines.append(line)
            if not reported and checkpoint_path.exists():
                print("CHECKPOINT_SAVED " + str(checkpoint_path), flush=True)
                reported = True
        code = process.wait()
        elapsed = time.perf_counter() - t0
        if code:
            raise RuntimeError(f"Original train_arrival.py exited {code}")
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        history = list(csv.DictReader((out / "history.csv").open()))
        manifest = json.loads((Path(cfg["data_dir"]).parent / "dataset_manifest.json").read_text())
        summary = {"training_wall_seconds": elapsed, "hardware": hw, "completed_epochs": len(history),
                   "best_epoch": checkpoint["epoch"], "validation": checkpoint["validation"],
                   "best_checkpoint": str(checkpoint_path),
                   "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
                   "sample_counts": manifest["sample_counts"],
                   "families": {s: sorted({r["scenario_family_id"] for r in manifest["simulations"]
                                           if r["accepted"] and r["split"] == s}) for s in ("train", "val", "test")},
                   "parameter_count": sum(t.numel() for t in checkpoint["model_state_dict"].values()),
                   "dataset_kind": "forefire", "scope": manifest["scope"]}
        (out / "training.log").write_text("".join(lines))
        (out / "run_summary.json").write_text(json.dumps(summary, indent=2))
        (out / "config_used.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
        shutil.copy2(Path(cfg["data_dir"]).parent / "dataset_manifest.json", out / "dataset_manifest.json")
        print("TRAINING_COMPLETED " + json.dumps(summary), flush=True)
    else:
        command = [sys.executable, str(ROOT / "ml/train_arrival.py"), "evaluate", "--config", str(args.config),
                   "--checkpoint", str(checkpoint_path)]
        t0 = time.perf_counter()
        evaluated = subprocess.run(command, cwd=ROOT / "ml", text=True, capture_output=True, check=True)
        stats = json.loads(evaluated.stdout)
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        stats.update(evaluation_wall_seconds=time.perf_counter() - t0,
                     inference_latency=latency(checkpoint, cfg))
        (out / "test_metrics.json").write_text(json.dumps(stats, indent=2))
        (out / "evaluation.log").write_text(evaluated.stdout + evaluated.stderr)
        print("EVALUATION_COMPLETED " + json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
