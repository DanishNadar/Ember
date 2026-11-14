"""Export scientific comparison images from a *real* ForeFire test split.

Run inside CUDA PyTorch job after training. No labels are fabricated; every PNG
is accompanied by sample metadata and per-horizon, held-out overlap metrics.
"""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from arrival_dataset import load_pair, discover, validate_checkpoint_contract
from arrival_model import ArrivalUNet


def sample_metrics(pred, truth):
    tp = int(np.logical_and(pred, truth).sum())
    fp = int(np.logical_and(pred, ~truth).sum())
    fn = int(np.logical_and(~pred, truth).sum())
    return {"iou": tp / (tp + fp + fn) if tp + fp + fn else 1.0,
            "precision": tp / (tp + fp) if tp + fp else (1.0 if fn == 0 else 0.0),
            "recall": tp / (tp + fn) if tp + fn else 1.0,
            "false_positive_pixels": fp, "false_negative_pixels": fn}


def render(sample_path, cfg, model, norm, device, output, horizons):
    x, reached, time_frac, meta = load_pair(sample_path, cfg)
    tensor = (x - np.asarray(norm["mean"], np.float32)[:, None, None]) / (
        np.asarray(norm["std"], np.float32)[:, None, None])
    with torch.inference_mode():
        logits, fraction = model(torch.from_numpy(tensor[None].astype(np.float32)).to(device))
        probability = torch.sigmoid(logits)[0, 0].cpu().numpy()
        pred_time = fraction[0, 0].cpu().numpy() * cfg["horizon_seconds"]
    truth_time = time_frac[0] * cfg["horizon_seconds"]
    hit = reached[0].astype(bool)
    true_display = np.where(hit, truth_time / 60, np.nan)
    pred_display = np.where(probability >= cfg["threshold"], pred_time / 60, np.nan)
    horizon = float(cfg["horizon_seconds"])
    final_pred = probability >= cfg["threshold"]
    final_truth = hit
    error = np.zeros_like(probability, dtype=np.uint8)
    error[final_truth & final_pred] = 1
    error[final_pred & ~final_truth] = 2
    error[final_truth & ~final_pred] = 3
    # Input axis 0=x/east; axis 1=y/north. Transpose to imshow rows=y, cols=x.
    fig, axs = plt.subplots(2, 3, figsize=(14, 9), constrained_layout=True)
    ignition = x[cfg["channel_names"].index(cfg["ignition_channel"])]
    axs[0, 0].imshow(ignition.T, cmap="gray_r", origin="lower", vmin=0, vmax=1)
    axs[0, 0].set_title("Initial ignition (input)")
    im = axs[0, 1].imshow(true_display.T, cmap="inferno", origin="lower", vmin=0, vmax=horizon / 60)
    axs[0, 1].set_title("ForeFire arrival (minutes)")
    fig.colorbar(im, ax=axs[0, 1], fraction=.045)
    im2 = axs[0, 2].imshow(pred_display.T, cmap="inferno", origin="lower", vmin=0, vmax=horizon / 60)
    axs[0, 2].set_title("Surrogate predicted arrival (minutes)")
    fig.colorbar(im2, ax=axs[0, 2], fraction=.045)
    from matplotlib.colors import ListedColormap, BoundaryNorm
    palette = ListedColormap(["#151824", "#20aa92", "#f29e4c", "#ee3c65"])
    axs[1, 0].imshow(error.T, origin="lower", cmap=palette, norm=BoundaryNorm(np.arange(-.5, 4.5), 4))
    axs[1, 0].set_title("Final burn mask: dark=TN, teal=TP, orange=FP, pink=FN")
    abs_error = np.where(hit, np.abs(pred_time - truth_time) / 60, np.nan)
    em = axs[1, 1].imshow(abs_error.T, cmap="magma", origin="lower", vmin=0)
    axs[1, 1].set_title("Absolute arrival error on true-reached cells (min)")
    fig.colorbar(em, ax=axs[1, 1], fraction=.045)
    measurements = []
    for h in horizons:
        t = hit & (truth_time <= h)
        p = final_pred & (pred_time <= h)
        measurements.append(dict(horizon_s=int(h), **sample_metrics(p, t)))
    axs[1, 2].plot([m["horizon_s"] / 60 for m in measurements],
                   [m["iou"] for m in measurements], "o-", label="IoU")
    axs[1, 2].plot([m["horizon_s"] / 60 for m in measurements],
                   [m["recall"] for m in measurements], "s--", label="Recall")
    axs[1, 2].set(xlabel="Forecast horizon (min)", ylabel="Score", ylim=(0, 1),
                   title="Real held-out mask accuracy over time")
    axs[1, 2].legend()
    axs[1, 2].grid(alpha=.2)
    for ax in axs.flat:
        if ax.images:
            ax.set(xlabel="Easting pixels", ylabel="Northing pixels")
    fig.suptitle("Ember · " + str(meta["simulation_id"]) +
                 " · ForeFire agreement only (not observed wildfire accuracy)")
    fig.savefig(output, dpi=125)
    plt.close(fig)
    return {"simulation_id": meta["simulation_id"], "scenario_family_id": meta["scenario_family_id"],
            "image": output.name, "horizons": measurements,
            "conditional_arrival_mae_seconds_on_true_reached": float(
                np.abs(pred_time - truth_time)[hit].mean()) if hit.any() else None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--dataset", type=Path, required=True, help="Root containing test/*.npz")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--limit", type=int, default=6)
    p.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    args = p.parse_args()
    if args.limit <= 0:
        p.error("limit must be positive")
    paths = sorted((args.dataset / "test").glob("*.npz"))[:args.limit]
    if not paths:
        raise ValueError("No genuine ForeFire test files found")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("GPU was requested but CUDA is unavailable")
    # Only load checkpoints from your own trusted training run.
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    cfg, norm = ckpt["config"], ckpt["normalization"]
    paths_by_split = discover(dict(cfg, data_dir=str(args.dataset.resolve())))
    validate_checkpoint_contract(ckpt, cfg, paths_by_split, args.checkpoint)
    model = ArrivalUNet(len(cfg["channel_names"]), cfg["base_filters"], cfg["depth"], cfg["dropout"]).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    out = args.output
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Use a new gallery output directory to preserve previous results")
    out.mkdir(parents=True, exist_ok=True)
    horizons = np.linspace(cfg["horizon_seconds"] / 6, cfg["horizon_seconds"], 6)
    results = [render(file, cfg, model, norm, device, out / (file.stem + ".png"), horizons)
               for file in paths]
    (out / "gallery_metrics.json").write_text(json.dumps(
        {"kind": "forefire_test_only", "checkpoint": str(args.checkpoint), "cases": results}, indent=2))
    print(f"Saved {len(results)} genuine test prediction galleries under {out}", flush=True)


if __name__ == "__main__":
    main()
