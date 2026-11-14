"""Train the supervised Ember U-Net; no simulation or Fuzzball code lives here."""
import argparse
import csv
import math
from pathlib import Path
import torch
from torch.utils.data import DataLoader
import yaml
from common import Metrics, SurrogateLoss, setup, write_json
from config import load_config
from dataset import BurnDataset, audit_splits, fit_normalization
from model import build_model


def run_epoch(model, loader, criterion, device, threshold, optimizer=None):
    model.train(optimizer is not None)
    total, samples = 0.0, 0
    metrics = Metrics(threshold)
    with torch.set_grad_enabled(optimizer is not None):
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y, x)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite loss: check inputs, normalization and learning_rate")
            if optimizer is not None:
                loss.backward()
                optimizer.step()
            total += loss.item() * len(x)
            samples += len(x)
            metrics.update(logits, y)
    return {"loss": total / samples, **metrics.result()}


def train(cfg):
    device = setup(cfg)
    splits, metadata = audit_splits(cfg)
    out = Path(cfg["output_dir"])
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"{out} is not empty; choose a new output_dir to preserve previous work")
    norm = fit_normalization(splits["train"], cfg)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "normalization.json", norm)
    (out / "config_used.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    write_json(out / "split_manifest.json", {split: [{"path": str(p), **metadata[str(p)]} for p in paths]
                                               for split, paths in splits.items()})
    generator = torch.Generator().manual_seed(cfg["random_seed"])
    train_loader = DataLoader(BurnDataset(splits["train"], cfg, norm), batch_size=cfg["batch_size"],
                              shuffle=True, num_workers=cfg["num_workers"], generator=generator)
    val_loader = DataLoader(BurnDataset(splits["val"], cfg, norm), batch_size=cfg["batch_size"],
                            shuffle=False, num_workers=cfg["num_workers"])
    model = build_model(cfg).to(device)
    if cfg["optimizer"] == "adam":
        optimizer = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"],
                                     betas=tuple(cfg["adam_betas"]), eps=cfg["optimizer_epsilon"])
    else:
        optimizer = torch.optim.SGD(model.parameters(), lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"],
                                    momentum=cfg["sgd_momentum"])
    criterion = SurrogateLoss(cfg)
    print(f"SUPERVISED SURROGATE | kind={cfg['dataset_kind']} | device={device} | "
          f"channels={len(cfg['channel_names'])} | parameters={sum(p.numel() for p in model.parameters()):,}", flush=True)
    print(f"Samples: train={len(splits['train'])}, val={len(splits['val'])}, test={len(splits['test'])} (test labels only audited, not fitted)", flush=True)
    if cfg["dataset_kind"] == "synthetic_mock":
        print("SYNTHETIC/MOCK PIPELINE TEST ONLY — no scientific accuracy claim", flush=True)
    best, patience_reference, stale, best_epoch = math.inf, math.inf, 0, 0
    with (out / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = None
        for epoch in range(1, cfg["epochs"] + 1):
            training = run_epoch(model, train_loader, criterion, device, cfg["threshold"], optimizer)
            validation = run_epoch(model, val_loader, criterion, device, cfg["threshold"])
            row = {"epoch": epoch, **{f"train_{k}": v for k, v in training.items()},
                   **{f"val_{k}": v for k, v in validation.items()}}
            if writer is None:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
            writer.writerow(row)
            handle.flush()
            checkpoint = {"format_version": 1, "epoch": epoch, "config": cfg, "normalization": norm,
                          "model_state_dict": model.state_dict(), "optimizer_state_dict": optimizer.state_dict(),
                          "validation_metrics": validation, "dataset_kind": cfg["dataset_kind"]}
            if validation["loss"] < best:
                best, best_epoch = validation["loss"], epoch
                torch.save(checkpoint, out / "best.pt")
            if epoch % cfg["save_frequency"] == 0:
                torch.save(checkpoint, out / f"epoch_{epoch:04d}.pt")
            torch.save(checkpoint, out / "last.pt")
            if validation["loss"] < patience_reference - cfg["early_stopping_min_delta"]:
                patience_reference, stale = validation["loss"], 0
            else:
                stale += 1
            print(f"Epoch {epoch:03d}/{cfg['epochs']} | train loss {training['loss']:.5f} | "
                  f"val loss {validation['loss']:.5f} | val IoU {validation['iou']:.4f} | "
                  f"val Dice {validation['dice_f1']:.4f} | best epoch {best_epoch}", flush=True)
            if stale >= cfg["early_stopping_patience"]:
                print(f"Early stopping after {stale} epochs without sufficient validation improvement", flush=True)
                break
    print(f"Saved best validation checkpoint: {out / 'best.pt'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        train(load_config(args.config))
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Training error: {exc}\n")


if __name__ == "__main__":
    main()
