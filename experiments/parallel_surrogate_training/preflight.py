"""PGX runtime probe; no training, dependency installation or configuration changes."""
import argparse
import json
import platform
import sys
import time


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--allow-cpu", action="store_true", help="Local code verification only")
    args = p.parse_args()
    import torch
    from model import build_model
    from data_contract import read_config
    from pathlib import Path
    cfg = read_config(Path(__file__).with_name("config.json"))
    if not torch.cuda.is_available() and not args.allow_cpu:
        p.exit(2, "CUDA unavailable. Fix the PGX container/driver environment; do not install CPU wheels.\n")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(2)
    cfg.update(base_filters=4, depth=2)
    model = build_model(cfg).to(device)
    x = torch.zeros(1, 19, 32, 32, device=device)
    start = time.perf_counter()
    y = model(x)
    y.square().mean().backward()
    if device.type == "cuda":
        torch.cuda.synchronize()
    if y.shape != (1, 2, 32, 32) or not torch.isfinite(y).all():
        raise ValueError("Model probe failed")
    print(json.dumps(dict(status="forward_backward_passed", python=sys.version, machine=platform.machine(),
                         torch=torch.__version__, device=str(device), cuda_build=torch.version.cuda,
                         gpu=torch.cuda.get_device_name() if device.type == "cuda" else None,
                         seconds=time.perf_counter()-start,
                         note="Compatibility probe only; not an accuracy or throughput benchmark"), indent=2))
