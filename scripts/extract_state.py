from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from simulation.state_extractor import extract_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract one ForeFire GeoJSON or KML state into Ember's raw/processed layout.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts"))
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--grid", type=int, default=256)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    result = extract_state(args.source, args.output_root, args.scenario_id, (args.grid, args.grid), args.resume)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
