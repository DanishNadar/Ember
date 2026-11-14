"""Train/evaluate direct-arrival U-Net. Run from Ember/ml.

Commands:
  python train_arrival.py train --config arrival_config.yaml
  python train_arrival.py evaluate --config arrival_config.yaml --checkpoint outputs_arrival/best.pt
"""
import argparse
import csv
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
import yaml

from arrival_dataset import ArrivalDataset, discover, fit_normalization
from arrival_model import ArrivalUNet, masked_arrival_loss
from observability import emit, resources


def config_from(path):
    p = Path(path).resolve()
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    cfg["data_dir"] = str((p.parent / cfg["data_dir"]).resolve())
    cfg["output_dir"] = str((p.parent / cfg["output_dir"]).resolve())
    if cfg["grid_size"] % (2 ** cfg["depth"]):
        raise ValueError("grid_size must be divisible by 2**depth")
    if len(cfg["channel_names"]) != len(cfg["channel_types"]):
        raise ValueError("channel types and channel names differ")
    if any(t not in ("binary", "continuous") for t in cfg["channel_types"]):
        raise ValueError("channel_types must be binary or continuous")
    if cfg["ignition_channel"] not in cfg["channel_names"]:
        raise ValueError("ignition channel absent")
    if cfg["horizon_seconds"] <= 0:
        raise ValueError("horizon must be positive")
    return cfg


def run_loader(net, loader, cfg, device, optimizer=None):
    net.train(optimizer is not None)
    total_loss, intersection, union, correct_time, reached_count, seen = 0., 0., 0., 0., 0., 0
    predicted_count, correct_count, pixel_count = 0., 0., 0.
    for x, burned, time in loader:
        x, burned, time = x.to(device), burned.to(device), time.to(device)
        with torch.set_grad_enabled(optimizer is not None):
            logits, predicted_t = net(x)
            loss = masked_arrival_loss(logits, predicted_t, burned, time, cfg)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite training loss")
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
        total_loss += loss.item() * len(x)
        pred = (torch.sigmoid(logits) >= cfg["threshold"])
        truth = burned.bool()
        intersection += (pred & truth).sum().item()
        union += (pred | truth).sum().item()
        predicted_count += pred.sum().item()
        correct_count += (pred == truth).sum().item()
        pixel_count += truth.numel()
        correct_time += ((predicted_t - time).abs() * burned).sum().item()
        reached_count += burned.sum().item()
        seen += len(x)
    precision = intersection / predicted_count if predicted_count else (1.0 if not reached_count else 0.0)
    recall = intersection / reached_count if reached_count else 1.0
    return {"loss": total_loss / seen, "iou": intersection / union if union else 1.,
            "dice": 2 * intersection / (predicted_count + reached_count) if (predicted_count + reached_count) else 1.,
            "precision": precision, "recall": recall,
            "pixel_accuracy": correct_count / pixel_count if pixel_count else None,
            "arrival_mae_seconds_on_reached": cfg["horizon_seconds"] * correct_time / reached_count if reached_count else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["train", "evaluate"])
    parser.add_argument("--config", default="arrival_config.yaml")
    parser.add_argument("--checkpoint", default=None)
    args = parser.parse_args()
    cfg = config_from(args.config)
    seed = cfg["random_seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    device = torch.device("cuda" if cfg["device"] == "auto" and torch.cuda.is_available() else
                          "cpu" if cfg["device"] == "auto" else cfg["device"])
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available")
    paths = discover(cfg)
    out = Path(cfg["output_dir"])
    event_path = out / "events.jsonl"
    if args.mode == "train":
        if out.exists() and any(out.iterdir()):
            raise ValueError("output_dir is not empty: choose a new output_dir to preserve checkpoints")
        out.mkdir(parents=True, exist_ok=True)
        norm = fit_normalization(paths["train"], cfg)
        (out / "normalization.json").write_text(json.dumps(norm, indent=2))
        emit("training_started", path=event_path, phase="gpu_training",
             sample_counts={key: len(files) for key, files in paths.items()},
             epochs_requested=cfg["epochs"], learning_rate=cfg["learning_rate"],
             device=str(device), resources=resources())
    else:
        if not args.checkpoint:
            parser.error("evaluate requires --checkpoint")
        checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
        if checkpoint["config"]["channel_names"] != cfg["channel_names"]:
            raise ValueError("Checkpoint channel names differ from current config")
        norm = checkpoint["normalization"]
    loaders = {part: DataLoader(ArrivalDataset(files, cfg, norm),
                               batch_size=cfg["batch_size"], shuffle=(part == "train" and args.mode == "train"),
                               num_workers=cfg["num_workers"]) for part, files in paths.items()}
    net = ArrivalUNet(len(cfg["channel_names"]), cfg["base_filters"], cfg["depth"], cfg["dropout"]).to(device)
    if args.mode == "evaluate":
        net.load_state_dict(checkpoint["model_state_dict"])
        emit("test_evaluation_started", path=event_path, echo=False, phase="final_test", resources=resources())
        stats = run_loader(net, loaders["test"], cfg, device)
        emit("test_evaluation_finished", path=event_path, echo=False, phase="final_test",
             metrics=stats, resources=resources())
        print(json.dumps({"dataset_kind": "forefire", "split": "test", **stats}, indent=2))
        return
    optimizer = torch.optim.Adam(net.parameters(), lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"])
    best = float("inf")
    with (out / "history.csv").open("w", newline="") as handle:
        fields = ["epoch"] + [p + "_" + k for p in ("train", "val") for k in
                  ("loss", "iou", "dice", "precision", "recall", "pixel_accuracy", "arrival_mae_seconds_on_reached")]
        fields += ["train_seconds", "validation_seconds", "learning_rate"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for epoch in range(1, cfg["epochs"] + 1):
            train_started = time.perf_counter()
            train = run_loader(net, loaders["train"], cfg, device, optimizer)
            train_seconds = time.perf_counter() - train_started
            val_started = time.perf_counter()
            val = run_loader(net, loaders["val"], cfg, device)
            validation_seconds = time.perf_counter() - val_started
            row = {"epoch": epoch, **{"train_" + k: v for k, v in train.items()},
                   **{"val_" + k: v for k, v in val.items()},
                   "train_seconds": train_seconds, "validation_seconds": validation_seconds,
                   "learning_rate": optimizer.param_groups[0]["lr"]}
            writer.writerow(row)
            handle.flush()
            emit("epoch_finished", path=event_path, phase="gpu_training", epoch=epoch,
                 train=train, val=val, train_seconds=train_seconds,
                 validation_seconds=validation_seconds, learning_rate=row["learning_rate"],
                 resources=resources())
            print(f"epoch {epoch}/{cfg['epochs']} train_loss={train['loss']:.4f} val_loss={val['loss']:.4f} IoU={val['iou']:.3f}", flush=True)
            if val["loss"] < best:
                best = val["loss"]
                torch.save({"model_state_dict": net.state_dict(), "config": cfg,
                            "normalization": norm, "epoch": epoch, "validation": val,
                            "model_kind": "direct_arrival_two_head"}, out / "best.pt")
                emit("checkpoint_saved", path=event_path, epoch=epoch, checkpoint=str(out / "best.pt"),
                     validation_loss=val["loss"])
    emit("training_finished", path=event_path, phase="gpu_training",
         best_checkpoint=str(out / "best.pt"), best_val_loss=best, resources=resources())
    print(f"Best checkpoint: {out / 'best.pt'}")


if __name__ == "__main__":
    main()
