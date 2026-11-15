"""One GPU experiment per process. Resume only BETWEEN frozen dataset rounds."""
import argparse
import json
import random
import platform
import socket
import sys
import time
from pathlib import Path
import numpy as np
from data_contract import read_config, snapshot, sample, normalization, digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    p.add_argument("--output", required=True, help="New output directory for this round")
    p.add_argument("--snapshot", help="Frozen snapshot.json shared by both candidates")
    p.add_argument("--resume", help="Previous round's last.pt; keeps optimizer and normalization")
    p.add_argument("--device", default="cuda", choices=("cpu", "cuda"))
    p.add_argument("--evaluate-test", action="store_true", help="Final selected run ONLY; never used for selection")
    args = p.parse_args()
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
    except ImportError:
        p.exit(2, "PyTorch missing. Use the PGX's validated CUDA/ARM64 environment. NumPy-only smoke.py still works.\n")
    from model import build_model
    cfg = read_config(args.config)
    if args.device == "cuda" and not torch.cuda.is_available():
        p.exit(2, "CUDA unavailable; no silent CPU fallback. Use --device cpu for debugging.\n")
    out = Path(args.output).resolve()
    if out.exists():
        p.exit(2, "Choose a NEW output directory; existing experiments are protected.\n")
    started = time.perf_counter()
    parts = snapshot(cfg)
    if args.snapshot:
        from data_contract import verify_frozen
        parts = verify_frozen(json.loads(Path(args.snapshot).read_text()), cfg)
    random.seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    torch.manual_seed(cfg["seed"])
    torch.set_num_threads(cfg["cpu_threads"])
    device = torch.device(args.device)
    model = build_model(cfg)
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"])
    norm = None
    old = None
    if args.resume:
        old = torch.load(args.resume, map_location=device, weights_only=False)  # trusted team checkpoints only
        keys = ("dataset_kind", "channel_names", "binary_channels", "grid_size", "horizon_seconds", "cell_size_meters",
                "base_filters", "depth", "arrival_weight", "dice_weight", "threshold", "learning_rate")
        if any(old["config"][k] != cfg[k] for k in keys):
            raise ValueError("Resume config mismatch; start a separate experiment for changed settings")
        for split in ("val", "test"):
            if parts[split] != old["snapshot"][split]:
                raise ValueError("Validation/test must remain unchanged across rounds")
        # Preserve prior training samples, content, and identities. Only append train samples.
        now = {r["metadata"]["sample_id"]: r for r in parts["train"]}
        for r in old["snapshot"]["train"]:
            if now.get(r["metadata"]["sample_id"]) != r:
                raise ValueError("Prior training data changed or removed")
        model.load_state_dict(old["model"])
        optimizer.load_state_dict(old["optimizer"])
        norm = old["normalization"]
        torch.set_rng_state(old["torch_rng"].cpu())
        if device.type == "cuda" and old.get("cuda_rng") is not None:
            torch.cuda.set_rng_state(old["cuda_rng"].cpu())
    norm = norm or normalization(parts["train"], cfg)
    mean = np.asarray(norm["mean"], np.float32)[:, None, None]
    std = np.asarray(norm["std"], np.float32)[:, None, None]

    class Samples(Dataset):
        def __init__(self, records):
            self.records = records

        def __len__(self):
            return len(self.records)

        def __getitem__(self, i):
            r = self.records[i]
            # Detect overwritten/incomplete data rather than training on a drifting snapshot.
            if digest(r["path"]) != r["sha256"]:
                raise ValueError("Frozen sample changed during training")
            x, arrival, valid, reached, _ = sample(r["path"], cfg)
            ignition = x[cfg["channel_names"].index("ignition")].copy()
            x = (x - mean) / std
            x[:, ~valid] = 0
            target = np.where(reached, arrival / cfg["horizon_seconds"], 0).astype(np.float32)
            return tuple(torch.from_numpy(a.astype(np.float32)) for a in
                         (x, target[None], valid[None], reached[None], ignition[None]))

    loaders = {k: DataLoader(Samples(v), batch_size=cfg["batch_size"], shuffle=k == "train", num_workers=0)
               for k, v in parts.items()}
    out.mkdir(parents=True)
    (out / "snapshot.json").write_text(json.dumps(parts, indent=2))
    (out / "config.json").write_text(json.dumps(cfg, indent=2))

    def event(name, **values):
        with (out / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(event=name, unix_seconds=time.time(), elapsed_seconds=time.perf_counter()-started,
                                   dataset_kind=cfg["dataset_kind"], device=str(device), **values)) + "\n")

    def epoch(loader, training):
        model.train(training)
        totals, losses, count, steps = {}, 0., 0, 0
        begin = time.perf_counter()
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        with torch.set_grad_enabled(training):
            for batch in loader:
                x, target, valid, reached, ignition = [a.to(device) for a in batch]
                raw = model(x)
                logits, predicted_t = raw[:, :1], raw[:, 1:].sigmoid()
                bce = (nn.functional.binary_cross_entropy_with_logits(logits, reached, reduction="none") * valid).sum() / valid.sum()
                prob = logits.sigmoid()
                dims = (1, 2, 3)
                dice = 1 - ((2*(prob*reached*valid).sum(dims)+1) / ((prob*valid).sum(dims)+(reached*valid).sum(dims)+1)).mean()
                reg = (nn.functional.smooth_l1_loss(predicted_t, target, reduction="none") * reached).sum() / reached.sum().clamp_min(1)
                loss = bce + cfg["dice_weight"]*dice + cfg["arrival_weight"]*reg
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite loss")
                if training:
                    optimizer.zero_grad(set_to_none=True)
                    loss.backward()
                    optimizer.step()
                losses += loss.item()*len(x)
                count += len(x)
                steps += 1
                if not training:
                    for seconds in sorted(set((600, 1200, 1800, cfg["horizon_seconds"]))):
                        if seconds > cfg["horizon_seconds"]:
                            continue
                        predicted = (prob >= cfg["threshold"]) & (predicted_t <= seconds/cfg["horizon_seconds"]) & valid.bool()
                        truth = reached.bool() & (target <= seconds/cfg["horizon_seconds"])
                        for label, mask in (("burn", valid.bool()), ("new_spread", valid.bool() & ~ignition.bool())):
                            a, b = predicted & mask, truth & mask
                            inter, union = (a & b).sum(dims), (a | b).sum(dims)
                            name = f"{label}_{seconds}s"
                            values = totals.setdefault(name, [0., 0., 0., 0., 0.])
                            values[0] += inter.sum().item()
                            values[1] += union.sum().item()
                            values[2] += torch.where(union > 0, inter / union.clamp_min(1), torch.ones_like(union, dtype=torch.float32)).sum().item()
                            # Persistence baseline: retain the initial ignition only.
                            persistence = ignition.bool() & mask
                            pi, pu = (persistence & b).sum(dims), (persistence | b).sum(dims)
                            values[3] += torch.where(pu > 0, pi / pu.clamp_min(1), torch.ones_like(pu, dtype=torch.float32)).sum().item()
                            values[4] += (union == 0).sum().item()
                    values = totals.setdefault("arrival", [0., 0.])
                    values[0] += ((predicted_t-target).abs()*reached).sum().item()*cfg["horizon_seconds"]
                    values[1] += reached.sum().item()
        if device.type == "cuda":
            torch.cuda.synchronize()
        result = dict(loss=losses/count, samples=count, optimizer_steps=steps if training else 0,
                      wall_seconds=time.perf_counter()-begin)
        result["samples_per_second"] = count/result["wall_seconds"]
        result["peak_torch_allocated_bytes"] = torch.cuda.max_memory_allocated() if device.type == "cuda" else None
        for name, v in totals.items():
            if name == "arrival":
                result["arrival_mae_seconds_on_reached"] = v[0]/v[1] if v[1] else None
            else:
                result[name] = dict(micro_iou=v[0]/v[1] if v[1] else 1., macro_iou=v[2]/count,
                                    persistence_macro_iou=v[3]/count, empty_union_samples=v[4])
        return result

    event("started", samples={k: len(v) for k, v in parts.items()}, resumed=bool(old),
          hostname=socket.gethostname(), machine=platform.machine(), python_version=platform.python_version(),
          torch_version=torch.__version__, gpu=torch.cuda.get_device_name() if device.type == "cuda" else None)
    best = float("inf")
    try:
        for e in range(cfg["epochs"]):
            train_stats = epoch(loaders["train"], True)
            val_stats = epoch(loaders["val"], False)
            checkpoint = dict(model=model.state_dict(), optimizer=optimizer.state_dict(), normalization=norm,
                              config=cfg, snapshot=parts, epoch=e+1, total_epochs=(old.get("total_epochs", old["epoch"]) if old else 0)+e+1, torch_rng=torch.get_rng_state(),
                              cuda_rng=torch.cuda.get_rng_state() if device.type == "cuda" else None)
            torch.save(checkpoint, out / "last.pt")
            if val_stats["loss"] < best:
                best = val_stats["loss"]
                torch.save(checkpoint, out / "best.pt")
            event("epoch", epoch=e+1, train=train_stats, validation=val_stats)
            print(json.dumps(dict(epoch=e+1, train_loss=train_stats["loss"], validation=val_stats)), flush=True)
        if args.evaluate_test:
            model.load_state_dict(torch.load(out / "best.pt", map_location=device, weights_only=False)["model"])
            result = epoch(loaders["test"], False)
            (out / "test_metrics.json").write_text(json.dumps(dict(dataset_kind=cfg["dataset_kind"], metrics=result), indent=2))
        event("finished", best_validation_loss=best)
    except Exception as exc:
        event("failed", error=str(exc))
        raise


if __name__ == "__main__":
    main()
