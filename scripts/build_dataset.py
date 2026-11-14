from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from processing.dataset_builder import build_next_state_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Build scenario-level split next-state datasets from Ember manifests.")
    parser.add_argument("manifest_directory", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    result = build_next_state_dataset(sorted(args.manifest_directory.glob("*.json")), args.output_root)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
