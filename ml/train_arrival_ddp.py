"""Opt-in two-node PyTorch DDP fine-tuning for the real ForeFire arrival model.

Launch one torchrun rank per Fuzzball node after an externally configured
rendezvous is reachable. This file does not assume Fuzzball can automatically
create a distributed process group. Resume requires a trusted checkpoint.
"""
import argparse
import csv
import os
from pathlib import Path
import random
import time

import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler, Subset

from arrival_dataset import ArrivalDataset, discover, fit_normalization
from arrival_model import ArrivalUNet, masked_arrival_loss
from observability import emit, resources
from train_arrival import config_from


def compute(model, loader, cfg, device, optimizer=None):
    model.train(optimizer is not None)
    # Sum loss by samples, pixel intersection/union, hits, and conditional time errors.
    totals = torch.zeros(8, dtype=torch.float64, device=device)
    for x, burn, arrival in loader:
        x = x.to(device)
        burn = burn.to(device)
        arrival = arrival.to(device)
        with torch.set_grad_enabled(optimizer is not None):
            logits, pred_time = model(x)
            loss = masked_arrival_loss(logits, pred_time, burn, arrival, cfg)
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
        pred = (torch.sigmoid(logits) >= cfg["threshold"])
        truth = burn.bool()
        totals += torch.tensor(
            [loss.item() * len(x), len(x),
             (pred & truth).sum().item(), (pred | truth).sum().item(),
             pred.sum().item(), burn.sum().item(),
             ((pred_time - arrival).abs() * burn).sum().item(),
             (pred == truth).sum().item() / truth.numel() * len(x)],
            dtype=torch.float64, device=device)
    dist.all_reduce(totals, op=dist.ReduceOp.SUM)
    loss, count, intersect, union, predicted, reached, abs_err, accuracy_samples = totals.tolist()
    return {"loss": loss / count if count else None,
            "iou": intersect / union if union else 1.0,
            "dice": 2 * intersect / (predicted + reached) if predicted + reached else 1.0,
            "precision": intersect / predicted if predicted else (1.0 if reached == 0 else 0.0),
            "recall": intersect / reached if reached else 1.0,
            "pixel_accuracy": accuracy_samples / count if count else None,
            "arrival_mae_seconds_on_reached": cfg["horizon_seconds"] * abs_err / reached if reached else None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True, help="New/empty checkpoint directory")
    p.add_argument("--resume", type=Path, default=None, help="Trusted pilot best.pt for true fine-tuning")
    p.add_argument("--epochs", type=int, default=10)
    args = p.parse_args()
    if args.epochs < 1:
        p.error("--epochs must be positive")
    for var in ("RANK", "LOCAL_RANK", "WORLD_SIZE", "MASTER_ADDR", "MASTER_PORT"):
        if var not in os.environ:
            p.error("Use torchrun with a working cross-node rendezvous; missing " + var)
    rank, local_rank, world = (int(os.environ[k]) for k in ("RANK", "LOCAL_RANK", "WORLD_SIZE"))
    if world < 2:
        p.error("DDP requires at least two ranks; single-GPU training uses train_arrival.py")
    if not torch.cuda.is_available():
        raise RuntimeError("DDP GPU training requires CUDA on every rank")
    torch.cuda.set_device(local_rank)
    device = torch.device("cuda", local_rank)
    dist.init_process_group(backend="nccl", init_method="env://")
    try:
        cfg = config_from(args.config)
        out = args.output.resolve()
        if rank == 0:
            if out.exists() and any(out.iterdir()):
                raise ValueError("Output directory must be new/empty: " + str(out))
            out.mkdir(parents=True, exist_ok=True)
        dist.barrier()
        seed = cfg["random_seed"]
        torch.manual_seed(seed)
        np.random.seed(seed)
        random.seed(seed)
        paths = discover(cfg)
        norm = fit_normalization(paths["train"], cfg) if rank == 0 else None
        obj = [norm]
        dist.broadcast_object_list(obj, src=0)
        norm = obj[0]
        train_set = ArrivalDataset(paths["train"], cfg, norm)
        val_set = ArrivalDataset(paths["val"], cfg, norm)
        sampler = DistributedSampler(train_set, num_replicas=world, rank=rank,
                                     shuffle=True, seed=seed, drop_last=True)
        if len(train_set) < world:
            raise ValueError("Too few train samples for world size")
        # Validation is partitioned with no padded/duplicated samples.
        val_indices = list(range(rank, len(val_set), world))
        train_loader = DataLoader(train_set, batch_size=cfg["batch_size"], sampler=sampler,
                                  num_workers=cfg["num_workers"])
        val_loader = DataLoader(Subset(val_set, val_indices), batch_size=cfg["batch_size"],
                                shuffle=False, num_workers=cfg["num_workers"])
        core = ArrivalUNet(len(cfg["channel_names"]), cfg["base_filters"], cfg["depth"], cfg["dropout"]).to(device)
        if args.resume:
            checkpoint = torch.load(args.resume, map_location="cpu", weights_only=False)
            if checkpoint["config"]["channel_names"] != cfg["channel_names"]:
                raise ValueError("Pretrained checkpoint channels differ")
            core.load_state_dict(checkpoint["model_state_dict"])
        model = DDP(core, device_ids=[local_rank])
        optimizer = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"],
                                      weight_decay=cfg["weight_decay"])
        event_path = out / "events.jsonl"
        phase = "ddp_finetune" if args.resume else "ddp_training"
        start_event = "ddp_finetune_started" if args.resume else "ddp_training_started"
        end_event = "ddp_finetune_finished" if args.resume else "ddp_training_finished"
        if rank == 0:
            emit(start_event, path=event_path, phase=phase, world_size=world,
                 checkpoint_loaded=str(args.resume) if args.resume else None,
                 resources=resources())
        best = float("inf")
        with (out / "history.csv").open("w", newline="", encoding="utf-8") if rank == 0 else open(os.devnull, "w") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "epoch", "train_loss", "val_loss", "train_iou", "val_iou", "train_dice", "val_dice",
                "train_precision", "val_precision", "train_recall", "val_recall",
                "train_pixel_accuracy", "val_pixel_accuracy",
                "train_arrival_mae_seconds_on_reached", "val_arrival_mae_seconds_on_reached",
                "train_seconds", "validation_seconds"])
            if rank == 0:
                writer.writeheader()
            for epoch in range(1, args.epochs + 1):
                sampler.set_epoch(epoch)
                t0 = time.perf_counter()
                train = compute(model, train_loader, cfg, device, optimizer)
                train_seconds = time.perf_counter() - t0
                t1 = time.perf_counter()
                val = compute(model, val_loader, cfg, device)
                val_seconds = time.perf_counter() - t1
                if rank == 0:
                    writer.writerow({"epoch": epoch, **{"train_" + k: v for k, v in train.items()},
                                     **{"val_" + k: v for k, v in val.items()},
                                     "train_seconds": train_seconds,
                                     "validation_seconds": val_seconds})
                    handle.flush()
                    emit("epoch_finished", path=event_path, phase=phase, epoch=epoch,
                         train=train, val=val, train_seconds=train_seconds,
                         validation_seconds=val_seconds, world_size=world, resources=resources())
                    if val["loss"] < best:
                        best = val["loss"]
                        torch.save({"model_state_dict": model.module.state_dict(),
                                    "config": cfg, "normalization": norm, "epoch": epoch,
                                    "validation": val, "model_kind": "direct_arrival_two_head",
                                    "training_mode": "ddp", "world_size": world},
                                   out / "best.pt")
                        emit("checkpoint_saved", path=event_path, phase=phase, epoch=epoch,
                             validation_loss=best)
                dist.barrier()
        if rank == 0:
            emit(end_event, path=event_path, phase=phase, world_size=world,
                 checkpoint=str(out / "best.pt"), best_val_loss=best, resources=resources())
    finally:
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
