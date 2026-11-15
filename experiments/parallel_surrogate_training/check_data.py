"""Validate real published data before reserving a GPU. No PyTorch required."""
import argparse
import json
from collections import Counter
from data_contract import read_config, snapshot


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    args = p.parse_args()
    try:
        cfg = read_config(args.config)
        parts = snapshot(cfg)
        print(json.dumps({"status": "contract_checks_passed", "dataset_kind": cfg["dataset_kind"],
                          "splits": {k: {"samples": len(v), "regions": dict(Counter(r["metadata"]["region"] for r in v))}
                                     for k, v in parts.items()},
                          "not_verified": ["physical accuracy", "geospatial alignment", "CUDA", "cluster speedup"]}, indent=2))
    except (ValueError, KeyError, OSError) as exc:
        p.exit(2, f"Data validation failed: {exc}\n")
