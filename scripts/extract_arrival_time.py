from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis.arrival_time import extract_arrival_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a ForeFire arrival_time_of_front NetCDF artifact.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts"))
    parser.add_argument("--fill-value", type=float, default=-9999.0)
    args = parser.parse_args()
    result = extract_arrival_time(args.source, args.output_root, args.artifact_id, args.fill_value)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
