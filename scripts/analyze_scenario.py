from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis.summary import analyze_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a completed Ember extraction manifest.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    print(json.dumps(analyze_scenario(args.manifest, args.output_root), indent=2))


if __name__ == "__main__":
    main()
