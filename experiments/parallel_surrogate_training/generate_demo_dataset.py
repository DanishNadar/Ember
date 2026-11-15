"""Generate a tiny, provenance-preserving ForeFire dataset for pipeline validation.

This is deliberately a research demonstration, not a replacement for the full
published data programme.  It labels one or more deterministic examples from
the checked-in ``dataset/ember_init_v2`` initial-state corpus with ForeFire,
rejects edge-hit cases, validates the parallel-surrogate contract, and only
then publishes a completed shard.
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

from data_contract import digest, read_config, sample, snapshot


DEFAULT_SOURCES = {
    "train": "corsica/train",
    "val": "texas_panhandle/val",
    "test": "montana_timber/test",
}


def sha256(path: Path) -> str:
    return digest(path)


def git_revision(repo: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def forefire_version() -> str:
    """The wheel owns the package version; pyforefire does not expose one."""
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


def publish(shard: Path, cfg: dict) -> list[dict]:
    entries = []
    for path in sorted(shard.glob("*.npz")):
        *_, meta = sample(path, cfg)
        entries.append({"file": path.name, "split": meta["split"], "sha256": sha256(path)})
    if not entries:
        raise ValueError("No valid labels were generated")
    temporary = shard / "complete.json.tmp"
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump({"status": "complete", "samples": entries}, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, shard / "complete.json")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="New immutable dataset-version directory")
    parser.add_argument("--dataset-version", default="forefire_demo_v1")
    parser.add_argument("--source-root", type=Path,
                        default=Path(__file__).resolve().parents[2] / "dataset" / "ember_init_v2")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--samples-per-split", type=int, default=1)
    args = parser.parse_args()

    if args.samples_per_split < 1:
        parser.error("--samples-per-split must be positive")
    output = args.output.resolve()
    source_root = args.source_root.resolve()
    config_path = args.config.resolve()
    if output.exists():
        parser.error(f"Output must be new for immutability: {output}")
    if not source_root.is_dir():
        parser.error(f"Missing initial-state source root: {source_root}")

    repo = Path(__file__).resolve().parents[2]
    dataset_root = source_root.parent
    sys.path.insert(0, str(dataset_root))
    try:
        import pyforefire
        from ember_bench import initstates, sim
    except ImportError as error:
        parser.error(f"ForeFire labelling dependency unavailable: {error}")
    installed_forefire_version = forefire_version()

    cfg = read_config(config_path)
    ready = output / "ready"
    shard = ready / "batch_000"
    shard.mkdir(parents=True)
    cfg["data_dir"] = str(ready)
    selected, rejected = [], []

    for split, source_split in DEFAULT_SOURCES.items():
        loaded = initstates.load_split(str(source_root), source_split)
        source_cfg = dict(loaded["meta"]["config"], _dir=initstates.ROOT)
        landscape = Path(initstates._p(source_cfg, source_cfg["landscape"]["path"]))
        properties = initstates.fuel_properties(
            initstates._p(source_cfg, source_cfg["landscape"]["fuel_table"]),
            source_cfg["landscape"].get("nonburnable", []),
            source_cfg["landscape"].get("engine", "corsica_native"),
        )
        source_hashes = {
            "samples_csv": sha256(source_root / source_split / "samples.csv"),
            "meta_json": sha256(source_root / source_split / "meta.json"),
            "landscape": sha256(landscape),
        }
        accepted = 0
        for row in loaded["rows"]:
            if accepted == args.samples_per_split:
                break
            scenario = initstates.to_scenario(row, source_cfg)
            result = sim.run_scenario(scenario)
            if result["edge_hit"]:
                rejected.append({"sample_id": row["sample_id"], "split": split, "reason": "edge_hit"})
                continue
            fuel, altitude, ignition = initstates.layers(row, source_cfg)
            x = initstates.input_tensor(row, fuel, altitude, ignition, properties, cfg["cell_size_meters"])
            arrival = result["arrival"].astype(np.float32)
            valid = np.ones(arrival.shape, dtype=np.uint8)
            reached = np.isfinite(arrival)
            target = np.where(reached, arrival, -9999).astype(np.float32)
            metadata = {
                "sample_id": row["sample_id"],
                "simulation_id": row["sample_id"],
                "scenario_family_id": f"region:{row['region']}",
                "region": row["region"],
                "engine_version": f"ForeFire {installed_forefire_version}; model={scenario['model']}",
                "edge_hit": False,
                "channel_names": cfg["channel_names"],
                "dataset_kind": "forefire",
                "horizon_seconds": cfg["horizon_seconds"],
                "cell_size_meters": cfg["cell_size_meters"],
                "array_order": "CXY",
                "arrival_units": "seconds",
                "split": split,
                "source_split": source_split,
                "source_hashes": source_hashes,
                "forefire_timing_seconds": {key: result[key] for key in ("t_import", "t_setup", "t_sim", "t_extract", "t_total")},
                "source_engine": source_cfg["landscape"].get("engine"),
                "source_landscape": str(landscape),
            }
            path = shard / f"{split}-{accepted:03d}-{row['sample_id']}.npz"
            write_npz_atomic(path, x=x, arrival_time_seconds=target, valid_mask=valid,
                             reached_mask=reached.astype(np.uint8),
                             metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)))
            sample(path, cfg)
            selected.append({"split": split, "sample_id": row["sample_id"], "file": path.name,
                             "source_split": source_split, "source_hashes": source_hashes})
            accepted += 1
        if accepted != args.samples_per_split:
            raise RuntimeError(f"Only {accepted} non-edge-hit labels found for {split}")

    entries = publish(shard, cfg)
    frozen = snapshot(cfg)
    provenance = {
        "dataset_version": args.dataset_version,
        "status": "complete",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": str(Path(__file__).resolve().relative_to(repo)),
        "repository_commit": git_revision(repo),
        "python": sys.version,
        "platform": platform.platform(),
        "forefire_version": installed_forefire_version,
        "config": {"path": str(config_path), "sha256": sha256(config_path)},
        "source_root": str(source_root),
        "sources": DEFAULT_SOURCES,
        "selected": selected,
        "rejected": rejected,
        "published_manifest": {"path": "ready/batch_000/complete.json", "sha256": sha256(shard / "complete.json"),
                               "entries": entries},
        "frozen_snapshot": {split: [{"file": Path(record["path"]).name, "sha256": record["sha256"],
                                      "metadata": record["metadata"]} for record in records]
                            for split, records in frozen.items()},
    }
    (output / "dataset_snapshot.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(output), "dataset_version": args.dataset_version,
                      "sample_counts": {split: len(records) for split, records in frozen.items()},
                      "manifest_sha256": provenance["published_manifest"]["sha256"]}, indent=2))


if __name__ == "__main__":
    main()
