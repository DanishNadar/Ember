"""Publish an already-complete, validated shard. One producer owns each shard."""
import argparse
import json
import os
from pathlib import Path
from data_contract import read_config, sample, digest


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    p.add_argument("--shard", required=True)
    args = p.parse_args()
    cfg = read_config(args.config)
    root = Path(args.shard).resolve()
    if (root / "complete.json").exists():
        raise ValueError("Shard already published; create a new shard")
    entries = []
    for path in sorted(root.glob("*.npz")):
        *_, meta = sample(path, cfg)
        if meta.get("split") not in ("train", "val", "test"):
            raise ValueError(f"{path}: metadata needs explicit split")
        entries.append(dict(file=path.name, split=meta["split"], sha256=digest(path)))
    if not entries:
        raise ValueError("Empty shard")
    temp = root / "complete.json.tmp"
    with temp.open("x", encoding="utf-8") as f:
        json.dump(dict(status="complete", samples=entries), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, root / "complete.json")
    print(f"Published {len(entries)} samples: {root}")
