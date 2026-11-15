"""Validate and freeze the fixed-family ForeFire research dataset release.

Run only after the six independently generated shards have been unpacked below
``<release>/ready``.  This never manufactures a manifest: every shard must
already have published its own ``complete.json`` after record validation.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from data_contract import digest, read_config, snapshot


EXPECTED_REGIONS = {
    "train": {"corsica", "socal_chaparral", "norcal_paradise", "greatbasin_nv"},
    "val": {"texas_panhandle"},
    "test": {"montana_timber"},
}


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
    parser.add_argument("--release", type=Path, required=True,
                        help="New version directory containing ready/<shard>/complete.json")
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--source-bundle-sha256", required=True)
    parser.add_argument("--code-bundle-sha256", required=True)
    args = parser.parse_args()

    release = args.release.resolve()
    ready = release / "ready"
    output = release / "dataset_snapshot.json"
    if output.exists():
        parser.error(f"Release is already frozen: {output}")
    if not ready.is_dir():
        parser.error(f"Missing ready directory: {ready}")
    cfg = read_config(args.config)
    cfg["data_dir"] = str(ready)
    parts = snapshot(cfg)
    actual_regions = {split: {record["metadata"]["region"] for record in records}
                      for split, records in parts.items()}
    if actual_regions != EXPECTED_REGIONS:
        raise ValueError(f"Fixed-family split mismatch: {actual_regions!r}")

    shard_reports, shard_manifests = [], []
    for manifest in sorted(ready.glob("*/complete.json")):
        report_path = manifest.parent / "generation_report.json"
        if not report_path.is_file():
            raise ValueError(f"Missing provenance report for {manifest.parent.name}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("status") != "generated" or report.get("failures"):
            raise ValueError(f"Incomplete generator report for {manifest.parent.name}")
        if report.get("dataset_version") != args.dataset_version:
            raise ValueError(f"Dataset-version mismatch in {manifest.parent.name}")
        if report.get("source_bundle_sha256") != args.source_bundle_sha256 or report.get("code_bundle_sha256") != args.code_bundle_sha256:
            raise ValueError(f"Input-bundle mismatch in {manifest.parent.name}")
        shard_reports.append({"shard": manifest.parent.name, "report_sha256": digest(report_path),
                              "report": report})
        shard_manifests.append({"shard": manifest.parent.name, "manifest_sha256": digest(manifest),
                                "sample_count": len(json.loads(manifest.read_text())["samples"])})

    release_record = {
        "dataset_version": args.dataset_version,
        "status": "complete",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_bundle_sha256": args.source_bundle_sha256,
        "code_bundle_sha256": args.code_bundle_sha256,
        "split_regions": {split: sorted(regions) for split, regions in actual_regions.items()},
        "sample_counts": {split: len(records) for split, records in parts.items()},
        "shard_manifests": shard_manifests,
        "shard_reports": shard_reports,
        "frozen_snapshot": parts,
    }
    write_json_atomic(output, release_record)
    print(json.dumps({"status": "complete", "dataset_version": args.dataset_version,
                      "sample_counts": release_record["sample_counts"],
                      "snapshot_sha256": digest(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
