"""Generate one immutable, contract-validated ForeFire-labelled data shard.

This is the production counterpart of ``generate_demo_dataset.py``.  It labels
one *predeclared* initial-state source with a fresh ForeFire process per
simulation, writes only valid non-edge-hit records, and emits ``complete.json``
only after every generated record passes the training data contract.  A failed
simulator run is fatal: it is recorded in ``generation_report.json`` but is
never silently omitted from a published shard.

The caller selects sources from the fixed experimental split plan.  The source
region is the scenario family; therefore it must occur in exactly one of
train, validation, or test across a dataset release.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np

from data_contract import digest, read_config, sample


def sha256(path: Path) -> str:
    return digest(path)


def git_revision(repo: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def forefire_version() -> str:
    try:
        return version("forefire")
    except PackageNotFoundError:
        return "unknown"


def write_npz_atomic(path: Path, **arrays: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as handle:
        np.savez_compressed(handle, **arrays)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New shard directory; it must not already exist")
    parser.add_argument("--source-root", type=Path, required=True,
                        help="Root containing the versioned initial-state corpus")
    parser.add_argument("--source", required=True,
                        help="Initial-state relative path, e.g. corsica/train")
    parser.add_argument("--split", choices=("train", "val", "test"), required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--workers", type=int, default=0,
                        help="ForeFire processes; 0 uses visible CPUs")
    parser.add_argument("--max-samples", type=int,
                        help="Bounded probe only; omitted means every source row")
    parser.add_argument("--start-index", type=int, default=0,
                        help="Zero-based source-row offset for a deterministic disjoint shard")
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--source-bundle-sha256",
                        help="Immutable Fuzzball source-bundle digest used for this run")
    parser.add_argument("--code-bundle-sha256",
                        help="Immutable Fuzzball generator-code bundle digest used for this run")
    args = parser.parse_args()

    if args.workers < 0 or args.start_index < 0 or (args.max_samples is not None and args.max_samples < 1):
        parser.error("--workers/start-index must be nonnegative and --max-samples positive")
    output = args.output.resolve()
    source_root = args.source_root.resolve()
    source_dir = (source_root / args.source).resolve()
    config_path = args.config.resolve()
    if output.exists():
        parser.error(f"Output must be new for immutability: {output}")
    if not source_dir.is_relative_to(source_root) or not (source_dir / "samples.csv").is_file():
        parser.error(f"Invalid initial-state source: {args.source}")

    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(source_root.parent))
    try:
        from ember_bench import initstates, runner
    except ImportError as error:
        parser.error(f"ForeFire labelling dependency unavailable: {error}")

    cfg = read_config(config_path)
    loaded = initstates.load_split(str(source_root), args.source)
    source_rows = loaded["rows"]
    stop = args.start_index + args.max_samples if args.max_samples is not None else None
    rows = source_rows[args.start_index:stop]
    if not rows:
        parser.error("No source rows selected")
    source_cfg = dict(loaded["meta"]["config"], _dir=initstates.ROOT)
    landscape = Path(initstates._p(source_cfg, source_cfg["landscape"]["path"]))
    properties = initstates.fuel_properties(
        initstates._p(source_cfg, source_cfg["landscape"]["fuel_table"]),
        source_cfg["landscape"].get("nonburnable", []),
        source_cfg["landscape"].get("engine", "corsica_native"),
    )
    source_hashes = {
        "samples_csv": sha256(source_dir / "samples.csv"),
        "meta_json": sha256(source_dir / "meta.json"),
        "landscape": sha256(landscape),
    }
    region = str(rows[0]["region"])
    if any(str(row["region"]) != region for row in rows):
        raise ValueError("A production shard must contain exactly one scenario family")

    output.mkdir(parents=True)
    expected = {str(row["sample_id"]): row for row in rows}
    scenarios = [initstates.to_scenario(row, source_cfg) for row in rows]
    accepted: list[dict] = []
    rejected: list[dict] = []
    failures: list[dict] = []
    for result in runner.run_many(scenarios, workers=args.workers, keep_arrays=True, progress=True):
        scenario = result["scenario"]
        sample_id = str(scenario["run_id"])
        row = expected[sample_id]
        if not result["ok"]:
            failures.append({"sample_id": sample_id, "error": result["error"]})
            continue
        if result["edge_hit"]:
            rejected.append({"sample_id": sample_id, "reason": "edge_hit"})
            continue
        fuel, altitude, ignition = initstates.layers(row, source_cfg)
        x = initstates.input_tensor(row, fuel, altitude, ignition, properties, cfg["cell_size_meters"])
        arrival = result["arrival"].astype(np.float32)
        valid = np.ones(arrival.shape, dtype=np.uint8)
        reached = np.isfinite(arrival)
        target = np.where(reached, arrival, -9999).astype(np.float32)
        metadata = {
            "sample_id": sample_id,
            "simulation_id": sample_id,
            "scenario_family_id": f"region:{region}",
            "region": region,
            "engine_version": f"ForeFire {forefire_version()}; model={scenario['model']}",
            "edge_hit": False,
            "channel_names": cfg["channel_names"],
            "dataset_kind": "forefire",
            "horizon_seconds": cfg["horizon_seconds"],
            "cell_size_meters": cfg["cell_size_meters"],
            "array_order": "CXY",
            "arrival_units": "seconds",
            "split": args.split,
            "source_split": args.source,
            "source_hashes": source_hashes,
            "source_engine": source_cfg["landscape"].get("engine"),
            "forefire_timing_seconds": {key: result[key] for key in
                                         ("t_import", "t_setup", "t_sim", "t_extract", "t_total")},
        }
        path = output / f"{args.split}-{sample_id}.npz"
        write_npz_atomic(path, x=x, arrival_time_seconds=target, valid_mask=valid,
                         reached_mask=reached.astype(np.uint8),
                         metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)))
        sample(path, cfg)
        accepted.append({"file": path.name, "split": args.split, "sha256": sha256(path),
                         "sample_id": sample_id})

    report = {
        "status": "failed" if failures else "generated",
        "dataset_version": args.dataset_version,
        "source": args.source,
        "split": args.split,
        "scenario_family_id": f"region:{region}",
        "requested": len(rows),
        "source_row_range": {"start": args.start_index, "stop_exclusive": args.start_index + len(rows),
                             "source_row_count": len(source_rows)},
        "accepted": len(accepted),
        "edge_hit_rejected": rejected,
        "failures": failures,
        "source_hashes": source_hashes,
        "source_bundle_sha256": args.source_bundle_sha256,
        "code_bundle_sha256": args.code_bundle_sha256,
        "forefire_version": forefire_version(),
        "repository_commit": git_revision(repo),
        "platform": platform.platform(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json_atomic(output / "generation_report.json", report)
    if failures:
        raise RuntimeError(f"ForeFire failed for {len(failures)} samples; no complete manifest published")
    if not accepted:
        raise RuntimeError("All simulator outputs were edge hits; no complete manifest published")
    accepted.sort(key=lambda entry: entry["file"])
    write_json_atomic(output / "complete.json", {"status": "complete", "samples": accepted})
    print(json.dumps({"status": "complete", "output": str(output), "requested": len(rows),
                      "accepted": len(accepted), "edge_hit_rejected": len(rejected),
                      "source": args.source, "split": args.split}, sort_keys=True))


if __name__ == "__main__":
    main()
