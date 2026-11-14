from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis.visuals import plot_completed_performance


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot wall-time and RSS only from completed measured ForeFire runs.")
    parser.add_argument("--run-root", type=Path, default=Path("artifacts/runs"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/figures/forefire_performance.png"))
    args = parser.parse_args()
    try:
        print(plot_completed_performance(args.run_root, args.output))
    except ValueError as error:
        print(f"Performance graph not created: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
