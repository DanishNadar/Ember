"""Evaluate held-out ForeFire labels, or explicitly marked synthetic smoke samples."""
import argparse
import json
from pathlib import Path
from time import perf_counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.utils.data import DataLoader
from common import Metrics, SurrogateLoss, load_checkpoint, setup, synchronize, write_json
from config import load_config
from dataset import BurnDataset, audit_splits


def save_figure(path, current, target, prediction, kind):
    figure, axes = plt.subplots(1, 4, figsize=(14, 4), constrained_layout=True)
    target_name = "ForeFire target" if kind == "forefire" else "Synthetic/mock target"
    for ax, image, title in zip(axes[:3], (current, target, prediction), ("Current burn at t", target_name, "Network prediction")):
        ax.imshow(image, cmap="gray", vmin=0, vmax=1, origin="lower")
        ax.set_title(title)
    error = prediction.astype(np.int8) - target.astype(np.int8)
    axes[3].imshow(error, cmap="bwr", vmin=-1, vmax=1, origin="lower")
    axes[3].set_title("Error: red FP, blue FN")
    for ax in axes:
        ax.set_axis_off()
    figure.suptitle("SYNTHETIC/MOCK — pipeline test only" if kind == "synthetic_mock" else "Surrogate agreement with ForeFire labels")
    figure.savefig(path, dpi=150)
    plt.close(figure)


def benchmark(model, x, cfg, device):
    with torch.inference_mode():
        for _ in range(cfg["latency_warmup_steps"]):
            model(x)
        synchronize(device)
        durations = []
        for _ in range(cfg["latency_repeats"]):
            synchronize(device)
            start = perf_counter()
            model(x)
            synchronize(device)
            durations.append((perf_counter() - start) * 1000)
    return {"device": str(device), "batch_size": len(x), "warmup_steps": cfg["latency_warmup_steps"],
            "repeats": cfg["latency_repeats"], "mean_batch_ms": float(np.mean(durations)),
            "median_batch_ms": float(np.median(durations)), "mean_ms_per_sample": float(np.mean(durations) / len(x)),
            "scope": "Forward only, first test batch, resident device tensors; excludes disk I/O, preprocessing, transfers, sigmoid and file export"}


def evaluate(cfg, checkpoint_path):
    device = setup(cfg)
    splits, metadata = audit_splits(cfg)
    model, norm, checkpoint = load_checkpoint(checkpoint_path, cfg, device)
    # Prevent evaluating files whose identities overlap this checkpoint's original training/val data,
    # even when a teammate changes data_dir after training.
    manifest_path = Path(checkpoint_path).resolve().parent / "split_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing {manifest_path}; retain the training split manifest for held-out auditing")
    trained = json.loads(manifest_path.read_text(encoding="utf-8"))
    group_key = checkpoint["config"]["split_group_key"]
    for key in ("simulation_id", group_key):
        used = {m[key] for split in ("train", "val") for m in trained[split]}
        for path in splits["test"]:
            if key not in metadata[str(path)]:
                raise ValueError(f"{path}: missing checkpoint split key {key}")
            if metadata[str(path)][key] in used:
                raise ValueError(f"Held-out leakage: test {key}={metadata[str(path)][key]!r} appeared in checkpoint training/validation")
    loader = DataLoader(BurnDataset(splits["test"], cfg, norm), batch_size=cfg["batch_size"],
                        shuffle=False, num_workers=cfg["num_workers"])
    out = Path(cfg["output_dir"]) / "evaluation"
    # Keep mock artifacts visibly separate even if output_dir changes.
    if cfg["dataset_kind"] == "synthetic_mock":
        out = out / "synthetic_mock"
    out.mkdir(parents=True, exist_ok=True)
    prediction_dir = out / "predictions"
    prediction_dir.mkdir(exist_ok=True)
    metrics = Metrics(cfg["threshold"])
    criterion = SurrogateLoss(cfg)
    total_loss, offset, latency = 0.0, 0, None
    burn_index = cfg["channel_names"].index(cfg["current_burn_channel"])
    with torch.inference_mode():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            if latency is None:
                latency = benchmark(model, x, cfg, device)
            logits = model(x)
            loss = criterion(logits, y, x)
            if not torch.isfinite(logits).all() or not torch.isfinite(loss):
                raise ValueError("Evaluation produced nonfinite logits/loss")
            paths = splits["test"][offset:offset + len(x)]
            metrics.update(logits, y, [metadata[str(p)].get("cell_size_meters") for p in paths])
            total_loss += loss.item() * len(x)
            probabilities = torch.sigmoid(logits).cpu().numpy()
            targets = y.cpu().numpy()
            current = x[:, burn_index].cpu().numpy()
            for i, path in enumerate(paths):
                prediction = (probabilities[i] >= cfg["threshold"]).astype(np.uint8)
                np.savez_compressed(prediction_dir / path.name, probability=probabilities[i], predicted_mask=prediction,
                                    target=targets[i], current_burn=current[i:i + 1],
                                    metadata_json=np.asarray(json.dumps(metadata[str(path)])))
                if offset + i == 0:
                    save_figure(out / "comparison.png", current[i], targets[i, 0], prediction[0], cfg["dataset_kind"])
            offset += len(x)
    result = {**metrics.result(), "loss": total_loss / offset, "threshold": cfg["threshold"],
              "dataset_kind": cfg["dataset_kind"], "is_real_benchmark": cfg["dataset_kind"] == "forefire",
              "interpretation": "Agreement with ForeFire labels; not real-world predictive accuracy" if cfg["dataset_kind"] == "forefire" else "SYNTHETIC/MOCK PIPELINE TEST ONLY; not a scientific benchmark",
              "checkpoint": str(Path(checkpoint_path).resolve()), "checkpoint_epoch": checkpoint["epoch"],
              "forecast_horizon_seconds": cfg["forecast_horizon_seconds"], "latency": latency}
    write_json(out / "metrics.json", result)
    print(f"{result['interpretation']}\nTest samples={offset} | IoU={result['iou']:.4f} | Dice={result['dice_f1']:.4f} | "
          f"area MAE={result['burned_area_mae_pixels']:.2f} pixels\n"
          f"Forward latency={latency['mean_ms_per_sample']:.3f} ms/sample on {device}\nArtifacts: {out}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    args = parser.parse_args()
    try:
        evaluate(load_config(args.config), args.checkpoint)
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Evaluation error: {exc}\n")


if __name__ == "__main__":
    main()
