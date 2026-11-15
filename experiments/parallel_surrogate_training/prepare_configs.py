"""Prepare a shared frozen data snapshot and two PGX candidate configurations."""
import argparse
import json
from pathlib import Path
from data_contract import read_config, snapshot


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default=str(Path(__file__).with_name("config.json")))
    p.add_argument("--data", required=True, help="Absolute shared-storage ready-shard directory")
    p.add_argument("--output", required=True, help="New shared experiment directory")
    args = p.parse_args()
    cfg = read_config(args.base)
    cfg["data_dir"] = str(Path(args.data).resolve())
    parts = snapshot(cfg)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "snapshot.json").write_text(json.dumps(parts, indent=2))
    for name, weight in (("A", 1.0), ("B", 2.0)):
        candidate = dict(cfg, arrival_weight=weight)
        (out / f"candidate_{name}.json").write_text(json.dumps(candidate, indent=2))
    print(f"Prepared A/B configs and frozen snapshot: {out}")
    print("Both candidates MUST use --snapshot with this file. This does not submit cluster jobs.")
