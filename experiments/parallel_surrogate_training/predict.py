"""Unlabeled inference, held-out evaluation and scoped forward-pass timing."""
import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch
from data_contract import inference_sample, sample, digest, read_config, verify_frozen
from model import build_model


def synchronize(device):
    if device.type == "cuda":
        torch.cuda.synchronize()


def metrics(prob, arrival, truth_arrival, valid, reached, ignition, cfg):
    out = {}
    for seconds in sorted(set((600, 1200, 1800, cfg["horizon_seconds"]))):
        if seconds > cfg["horizon_seconds"]:
            continue
        pred = (prob >= cfg["threshold"]) & (arrival <= seconds) & valid
        truth = reached & (truth_arrival <= seconds)
        for name, area in (("burn", valid), ("new_spread", valid & ~ignition)):
            a, b = pred & area, truth & area
            tp = int((a & b).sum())
            fp, fn = int((a & ~b).sum()), int((~a & b).sum())
            persistence = ignition & area
            pi, pu = int((persistence & b).sum()), int((persistence | b).sum())
            out[f"{name}_{seconds}s"] = dict(tp=tp, fp=fp, fn=fn, iou=tp/(tp+fp+fn) if tp+fp+fn else 1.,
                                             recall=tp/(tp+fn) if tp+fn else None,
                                             empty_truth=not bool(b.any()),
                                             persistence_iou=pi/pu if pu else 1.)
    errors = np.abs(arrival[reached]-truth_arrival[reached])
    out["arrival"] = dict(abs_error_seconds_sum=float(errors.sum()), reached_cells=int(reached.sum()),
                          mae_seconds=float(errors.mean()) if len(errors) else None)
    return out


def aggregate(rows):
    out = {}
    for key in rows[0]:
        if key == "arrival":
            count = sum(r[key]["reached_cells"] for r in rows)
            out[key] = dict(mae_seconds_on_reached=sum(r[key]["abs_error_seconds_sum"] for r in rows)/count if count else None,
                            reached_cells=count)
        else:
            tp, fp, fn = (sum(r[key][k] for r in rows) for k in ("tp", "fp", "fn"))
            out[key] = dict(micro_iou=tp/(tp+fp+fn) if tp+fp+fn else 1.,
                            macro_iou=float(np.mean([r[key]["iou"] for r in rows])),
                            micro_recall=tp/(tp+fn) if tp+fn else None,
                            persistence_macro_iou=float(np.mean([r[key]["persistence_iou"] for r in rows])),
                            empty_truth_samples=sum(r[key]["empty_truth"] for r in rows), tp=tp, fp=fp, fn=fn)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--output", required=True)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Unlabeled NPZ: x, valid_mask, metadata_json")
    source.add_argument("--split", choices=("val", "test"))
    p.add_argument("--config", help="Required with --split; use to resolve or verify the dataset")
    p.add_argument("--device", default="cuda", choices=("cpu", "cuda"))
    p.add_argument("--repeats", type=int, default=20)
    p.add_argument("--warmup", type=int, default=3)
    args = p.parse_args()
    if args.repeats < 1 or args.warmup < 0:
        p.error("Invalid timing repeat counts")
    if args.device == "cuda" and not torch.cuda.is_available():
        p.exit(2, "CUDA unavailable; no CPU fallback.\n")
    device = torch.device(args.device)
    # Checkpoints contain optimizer/config Python objects: trusted team sources only.
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    cfg = checkpoint["config"]
    torch.set_num_threads(cfg["cpu_threads"])
    if args.split:
        if not args.config:
            p.error("--split requires --config")
        current = read_config(args.config)
        for k in ("channel_names", "binary_channels", "grid_size", "horizon_seconds", "cell_size_meters", "dataset_kind"):
            if current[k] != cfg[k]:
                raise ValueError(f"Evaluation config mismatch: {k}")
        # Evaluate the original immutable split, never silently substitute a new one.
        records = verify_frozen(checkpoint["snapshot"], cfg)[args.split]
    else:
        records = [{"path": str(Path(args.input).resolve())}]
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    norm = checkpoint["normalization"]
    mean = np.asarray(norm["mean"], np.float32)[:, None, None]
    std = np.asarray(norm["std"], np.float32)[:, None, None]
    if mean.shape != (len(cfg["channel_names"]), 1, 1) or std.shape != mean.shape or not np.isfinite(mean).all() or not np.isfinite(std).all() or np.any(std <= 0) or norm.get("fit_split") != "train":
        raise ValueError("Invalid checkpoint normalization")
    model = build_model(cfg).to(device).eval()
    model.load_state_dict(checkpoint["model"])
    results, timings, groups = [], [], defaultdict(list)
    with torch.inference_mode():
        for i, record in enumerate(records):
            synchronize(device)
            start = time.perf_counter()
            x, valid, meta = inference_sample(record["path"], cfg)
            ignition = x[cfg["channel_names"].index("ignition")].astype(bool)
            x = (x-mean)/std
            x[:, ~valid] = 0
            tensor = torch.from_numpy(x[None]).to(device)
            if i == 0:
                # Warmup/timing runs are excluded from the end-to-end measurement below.
                synchronize(device)
                preparation_seconds = time.perf_counter()-start
                for _ in range(args.warmup):
                    model(tensor)
                durations = []
                for _ in range(args.repeats):
                    synchronize(device)
                    tick = time.perf_counter()
                    model(tensor)
                    synchronize(device)
                    durations.append(time.perf_counter()-tick)
                start = time.perf_counter()-preparation_seconds
                timings = durations
            raw = model(tensor)
            prob = raw[0, 0].sigmoid().cpu().numpy()
            arrival = raw[0, 1].sigmoid().cpu().numpy()*cfg["horizon_seconds"]
            predicted_burn = (prob >= cfg["threshold"]) & valid
            # Arrival is conditional on reaching; NaN outside predicted burn is for display ONLY.
            display_arrival = np.where(predicted_burn, arrival, np.nan).astype(np.float32)
            np.savez_compressed(out / f"prediction_{i:06d}.npz", burn_score=prob,
                                conditional_arrival_seconds=arrival, predicted_burn=predicted_burn,
                                display_arrival_seconds=display_arrival, valid_mask=valid,
                                metadata_json=np.asarray(json.dumps(meta)))
            synchronize(device)
            row = dict(sample_id=meta["sample_id"], region=meta["region"],
                       end_to_end_seconds=time.perf_counter()-start)
            if args.split:
                _, target, mask, reached, _ = sample(record["path"], cfg)
                row["metrics"] = metrics(prob, arrival, target, mask, reached, ignition, cfg)
                groups[meta["region"]].append(row["metrics"])
            results.append(row)
    report = dict(dataset_kind=cfg["dataset_kind"], device=str(device), split=args.split,
                  checkpoint_sha256=digest(args.checkpoint), samples=results,
                  interpretation="Agreement with simulator outputs, NOT real-world wildfire accuracy" if cfg["dataset_kind"] == "forefire" else "SYNTHETIC PIPELINE TEST ONLY",
                  latency=dict(batch_size=1, forward_median_seconds=float(np.median(timings)),
                               forward_p95_seconds=float(np.quantile(timings, .95)), repeats=args.repeats,
                               forward_scope="First scenario, resident tensor, network only; CUDA synchronized",
                               end_to_end_scope="NPZ read, normalization, transfers, forward, sigmoid, compressed output write; excludes checkpoint startup, warmups, repeated timing and label evaluation",
                               end_to_end_median_seconds=float(np.median([r["end_to_end_seconds"] for r in results]))))
    if args.split:
        report["overall"] = aggregate([r["metrics"] for r in results])
        report["by_region"] = {k: aggregate(v) for k, v in groups.items()}
    (out / "report.json").write_text(json.dumps(report, indent=2))
    print(f"Saved {len(results)} predictions and report.json to {out}")


if __name__ == "__main__":
    main()
