from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from simulation.netcdf_extractor import extract_environment, inspect_landscape


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a ForeFire HDF5-backed NetCDF landscape and align recognized fields to an Ember state.")
    parser.add_argument("landscape", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    result = {"inspection": inspect_landscape(args.landscape), "environment": extract_environment(args.landscape, args.manifest)}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["environment"]["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
