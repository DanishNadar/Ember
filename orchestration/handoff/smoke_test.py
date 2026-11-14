"""Minimal portable test for dependency handoff. No ForeFire or GPU required."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    with tempfile.TemporaryDirectory(prefix="ember-handoff-") as tmp:
        root = Path(tmp)
        # Artificial delays are only to show event ordering, not to benchmark compute.
        commands = {
            "simulate": [sys.executable, "-c", "import time; time.sleep(0.15); print('DEMO simulator done')"],
            "baseline": [sys.executable, "-c", "import time; time.sleep(0.4); print('DEMO baseline complete')"],
            "secondary": [sys.executable, "-c", "import time; time.sleep(0.02); print('DEMO extra trial complete')"],
            "output_dir": "results",
        }
        conf = root / "smoke.json"
        conf.write_text(json.dumps(commands))
        runner = Path(__file__).with_name("run_local.py")
        subprocess.run([sys.executable, str(runner), "--config", str(conf)], check=True)
        events = json.loads((root / "results/events.json").read_text())["events"]
        sim_finish = next(e for e in events if e["event"] == "finished" and e["job"] == "simulate")
        secondary_start = next(e for e in events if e["event"] == "started" and e["job"] == "secondary")
        baseline_start = next(e for e in events if e["event"] == "started" and e["job"] == "baseline")
        assert baseline_start["offset_seconds"] <= sim_finish["offset_seconds"]
        assert secondary_start["offset_seconds"] >= sim_finish["offset_seconds"]
        print("PASS: independent jobs start concurrently; secondary begins after simulator finishes.")
        print("NOTE: mock job timing is not evidence of performance or GPU use.")


if __name__ == "__main__":
    main()
