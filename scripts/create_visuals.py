from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis.visuals import create_reference_visuals


def main() -> None:
    parser = argparse.ArgumentParser(description="Create presentation-ready Ember visuals from verified reference artifacts.")
    parser.add_argument("--state-manifest", type=Path, default=Path("artifacts/manifests/forefire_runff_reference.json"))
    parser.add_argument("--arrival-manifest", type=Path, default=Path("artifacts/arrival/forefire_runff_arrival_reference.json"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    print(json.dumps(create_reference_visuals(args.state_manifest, args.arrival_manifest, args.output_root), indent=2))


if __name__ == "__main__":
    main()
