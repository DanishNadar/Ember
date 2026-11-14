"""Local proof of Ember's resource-handoff dependency graph.

Runs the simulator and baseline concurrently. Once the simulator exits successfully,
starts an independent ML trial while the baseline may still be running.

This is a local orchestration smoke test, NOT Fuzzball, GPU utilization evidence,
or an implementation of DDP. The cluster Fuzzfile is documented separately.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time


def stamp():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="JSON config with simulate, baseline, secondary commands")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent
    out = (root / cfg.get("output_dir", "handoff_results")).resolve()
    if out.exists() and any(out.iterdir()):
        parser.error(f"{out} is not empty; choose another output_dir to preserve evidence")
    for name in ("simulate", "baseline", "secondary"):
        if name not in cfg or not isinstance(cfg[name], list) or not cfg[name] or not all(
            isinstance(part, str) and part for part in cfg[name]
        ):
            parser.error(f"{name} must be a nonempty JSON array of command arguments")
    out.mkdir(parents=True, exist_ok=True)
    events = []
    open_files = {}
    processes = {}
    start = time.perf_counter()

    def mark(kind, name, **details):
        e = {"event": kind, "job": name, "time_utc": stamp(),
             "offset_seconds": round(time.perf_counter() - start, 4), **details}
        events.append(e)
        print(f"[{e['offset_seconds']:.3f}s] {kind}: {name}", flush=True)

    def begin(name):
        path = out / f"{name}.log"
        stream = path.open("w", encoding="utf-8")
        open_files[name] = stream
        proc = subprocess.Popen(cfg[name], cwd=root, stdout=stream, stderr=subprocess.STDOUT)
        processes[name] = proc
        mark("started", name, pid=proc.pid, command=cfg[name])
        return proc

    def finish(name):
        returncode = processes[name].wait()
        mark("finished" if returncode == 0 else "failed", name, returncode=returncode)
        return returncode

    error = None
    try:
        begin("simulate")
        begin("baseline")
        sim_code = finish("simulate")
        if sim_code == 0:
            # Exactly the Fuzzball dependency used in the cluster Fuzzfile.
            begin("secondary")
            secondary_code = finish("secondary")
            if secondary_code != 0:
                error = "Secondary ML trial failed"
        else:
            mark("skipped", "secondary", reason="Simulation failed")
            error = "Simulator stage failed"
        if finish("baseline") != 0:
            error = (error + "; " if error else "") + "Baseline ML trial failed"
    finally:
        for proc in processes.values():
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        for stream in open_files.values():
            stream.close()
        report = {"schema_version": 1, "mode": "local_dependency_smoke_test",
                  "is_fuzzball_run": False, "measures_gpu_utilization": False,
                  "started_at_utc": events[0]["time_utc"] if events else None,
                  "elapsed_seconds": round(time.perf_counter() - start, 4),
                  "events": events, "error": error}
        (out / "events.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("Evidence: " + str(out / "events.json"))
    if error:
        raise SystemExit(error)


if __name__ == "__main__":
    main()
