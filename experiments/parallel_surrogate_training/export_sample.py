"""Explicit adapter: prepared input NPZ + numeric ForeFire arrival NPY -> labeled sample.

Does not run ForeFire or infer its sentinel, orientation or physical units.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from data_contract import read_config, inference_sample, sample


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    p.add_argument("--inputs", required=True, help="Unnormalized x, valid_mask, metadata_json NPZ")
    p.add_argument("--arrival", required=True, help="NPY already aligned to input XY grid")
    p.add_argument("--source-units", required=True, choices=("seconds", "minutes"))
    p.add_argument("--source-unreached", required=True, type=float, help="Explicit sentinel e.g. inf or -9999")
    p.add_argument("--split", required=True, choices=("train", "val", "test"))
    p.add_argument("--output", required=True, help="New NPZ inside an unpublished shard")
    args = p.parse_args()
    cfg = read_config(args.config)
    x, valid, meta = inference_sample(args.inputs, cfg)
    arrival = np.load(args.arrival, allow_pickle=False)
    if arrival.shape != valid.shape or arrival.dtype.kind not in "fi":
        raise ValueError("Arrival shape/type mismatch; do not silently resize or transpose")
    never = np.isnan(arrival) if np.isnan(args.source_unreached) else arrival == args.source_unreached
    seconds = arrival.astype(np.float64)*(60 if args.source_units == "minutes" else 1)
    if np.any(valid & ~never & (~np.isfinite(seconds) | (seconds < 0))):
        raise ValueError("Unrecognized nonfinite/negative arrival; confirm engine sentinel and ignition values")
    reached = valid & ~never & (seconds <= cfg["horizon_seconds"])
    target = np.where(reached, seconds, -9999).astype(np.float32)
    meta["split"] = args.split
    meta["source_arrival_units"] = args.source_units
    meta["source_unreached_sentinel"] = str(args.source_unreached)
    path = Path(args.output).resolve()
    if path.suffix != ".npz" or path.exists() or (path.parent / "complete.json").exists():
        raise ValueError("Use a new NPZ in an unpublished shard")
    # Validate everything before writing the destination.
    for key in ("simulation_id", "scenario_family_id"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ValueError(f"Missing {key}")
    if meta.get("edge_hit") is not False:
        raise ValueError("Invalid/unconfirmed edge-hit status")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, x=x, arrival_time_seconds=target, valid_mask=valid.astype(np.uint8),
                        reached_mask=reached.astype(np.uint8), metadata_json=np.asarray(json.dumps(meta)))
    sample(path, cfg)
    print(f"Validated labeled sample: {path}. Publish shard only when every sample is ready.")
