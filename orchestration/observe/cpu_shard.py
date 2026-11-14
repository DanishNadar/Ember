"""Run real ForeFire training-region scenarios on a bounded CPU shard.

Each Fuzzball shard uses an isolated scratch volume. Shards split the *same*
training regions by stable sample hash, not by mixing validation/test families.
No CPU result is fed into an already-running GPU model; merge and retrain later.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dataset"))
sys.path.insert(0, str(ROOT / "ml"))
from ember_bench import initstates, runner
from observability import emit, resources

TRAIN_REGIONS = ["corsica", "socal_chaparral", "norcal_paradise", "greatbasin_nv"]
SENTINEL = -9999.0


def owner(sample_id, shards):
    return int(hashlib.sha256(sample_id.encode("utf-8")).hexdigest(), 16) % shards


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as inp:
        for chunk in iter(lambda: inp.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shards", type=int, default=2)
    p.add_argument("--workers", type=int, default=12)
    p.add_argument("--per-region", type=int, default=80,
                   help="Max attempted scenarios PER region across all shards")
    p.add_argument("--source", type=Path, default=ROOT / "dataset/ember_init_v2")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.shards < 1 or not 0 <= args.shard < args.shards or args.workers < 1 or args.per_region < 1:
        p.error("Invalid shards, shard index, workers or per-region limit")
    if not args.source.is_dir():
        raise FileNotFoundError(f"ForeFire source dataset not found: {args.source}")
    out = args.output
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing shard: {out}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "data/train").mkdir(parents=True, exist_ok=True)
    events = out / "events.jsonl"
    started = time.perf_counter()
    names = [name for name, _ in initstates.CHANNELS]
    records = []
    emit("cpu_shard_started", path=events, phase="cpu_physics",
         shard=args.shard, shards=args.shards, workers=args.workers,
         source=str(args.source), host=socket.gethostname(), resources=resources())
    for region in TRAIN_REGIONS:
        src_split = "train"
        loaded = initstates.load_split(str(args.source), f"{region}/{src_split}")
        cfg = dict(loaded["meta"]["config"], _dir=initstates.ROOT)
        props = initstates.fuel_properties(
            initstates._p(cfg, cfg["landscape"]["fuel_table"]),
            cfg["landscape"].get("nonburnable", []), cfg["landscape"].get("engine", "corsica_native"))
        rows = sorted(loaded["rows"], key=lambda r: hashlib.sha256(
            ("ember-cpu-shard-v1:" + r["sample_id"]).encode()).hexdigest())
        selected = [r for r in rows[:args.per_region] if owner(r["sample_id"], args.shards) == args.shard]
        for offset in range(0, len(selected), args.workers * 2):
            batch = selected[offset:offset + args.workers * 2]
            by_id = {r["sample_id"]: r for r in batch}
            batch_start = time.perf_counter()
            for result in runner.run_many([initstates.to_scenario(r, cfg) for r in batch],
                                          workers=args.workers, progress=False):
                sc = result["scenario"]
                row = by_id[sc["run_id"]]
                rec = {"sample_id": row["sample_id"], "region": region, "split": "train",
                       "shard": args.shard, "ok": bool(result.get("ok")),
                       "edge_hit": bool(result.get("edge_hit", False)),
                       "worker_seconds": result.get("t_worker")}
                if rec["ok"] and not rec["edge_hit"]:
                    ignition = initstates.ignition_mask(row, cfg)
                    x = initstates.input_tensor(
                        row, result["fuel"], result["alt"], ignition, props, cfg["grid"]["dx_m"])
                    arrival = np.where(np.isfinite(result["arrival"]),
                                       result["arrival"], SENTINEL).astype(np.float32)
                    if x.dtype != np.float32 or x.shape != (len(names), 320, 320):
                        raise ValueError("Simulator input shape mismatch: " + row["sample_id"])
                    if arrival.shape != (320, 320) or not np.all(
                            (arrival == SENTINEL) | ((arrival >= 0) & (arrival <= sc["horizon_s"]))):
                        raise ValueError("Simulator arrival-time grid invalid: " + row["sample_id"])
                    target = out / "data/train" / (row["sample_id"] + ".npz")
                    np.savez_compressed(
                        target, x=x, arrival_time_seconds=arrival, channel_names=np.asarray(names),
                        simulation_id=np.asarray(row["sample_id"]),
                        scenario_family_id=np.asarray("region:" + region),
                        dataset_kind=np.asarray("forefire"),
                        horizon_seconds=np.asarray(sc["horizon_s"]),
                        cell_size_meters=np.asarray(sc["dx"]),
                        array_index_order=np.asarray("[channel,x_east,y_north]"),
                        wind_shift_ramp_seconds=np.asarray(sc["wind_shift_ramp_s"]))
                    rec["file"] = str(target.relative_to(out))
                    rec["sha256"] = sha256_file(target)
                else:
                    rec["reason"] = str(result.get("error", "edge_hit"))
                records.append(rec)
                emit("cpu_simulation_finished", path=events, phase="cpu_physics",
                     shard=args.shard, region=region, sample_id=row["sample_id"],
                     status="complete" if "file" in rec else "excluded",
                     simulation_ok=rec["ok"], edge_hit=rec["edge_hit"],
                     worker_seconds=rec["worker_seconds"])
            emit("cpu_batch_finished", path=events, phase="cpu_physics",
                 shard=args.shard, region=region, completed=len(records),
                 batch_seconds=time.perf_counter() - batch_start, resources=resources())
    summary = {"status": "complete", "shard": args.shard, "shards": args.shards,
               "workers_requested": args.workers, "host": socket.gethostname(),
               "wall_seconds": time.perf_counter() - started,
               "attempts": len(records), "accepted": sum("file" in r for r in records),
               "rejected": sum("file" not in r for r in records),
               "regions": TRAIN_REGIONS, "scope": "real ForeFire training-region runs only",
               "notes": "Outputs require dataset-contract verification and a later training run"}
    (out / "manifest.json").write_text(json.dumps({"summary": summary, "records": records}, indent=2))
    emit("cpu_shard_finished", path=events, phase="cpu_physics",
         shard=args.shard, summary=summary, resources=resources())
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
