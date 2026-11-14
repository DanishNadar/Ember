from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from simulation.forefire_runner import run_forefire


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a ForeFire CLI scenario while measuring wall time and process RSS.")
    parser.add_argument("script", type=Path)
    parser.add_argument("--executable", default="forefire")
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()
    result = run_forefire(args.executable, args.script, args.run_directory, args.timeout_seconds)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
