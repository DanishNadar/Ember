"""Structured, append-only observability for real Ember jobs.

The JSON line and stdout marker carry the same event. No synthetic measurements
are inserted when a metric or device is unavailable.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import math
from datetime import datetime, timezone


PREFIX = "EMBER_EVENT "


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def resources():
    """A point-in-time snapshot, NOT average CPU/GPU utilization."""
    info = {"host": socket.gethostname(), "pid": os.getpid(),
            "host_logical_cpus": os.cpu_count(),
            "cpu_allocated": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None}
    try:
        import psutil
        proc = psutil.Process()
        info.update(process_rss_mb=round(proc.memory_info().rss / 1048576, 2),
                    host_cpu_percent_snapshot=psutil.cpu_percent(interval=0.1),
                    cpu_sample_interval_seconds=0.1,
                    host_memory_percent_snapshot=psutil.virtual_memory().percent)
    except (ImportError, OSError):
        pass
    try:
        p = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3)
        if p.returncode == 0 and p.stdout.strip():
            vals = [v.strip() for v in p.stdout.splitlines()[0].split(",")]
            for key, value in zip(("gpu_utilization_percent_snapshot", "gpu_memory_used_mib_snapshot",
                                   "gpu_memory_total_mib"), vals):
                try:
                    number = float(value)
                    if math.isfinite(number) and number >= 0:
                        info[key] = number
                except ValueError:
                    pass  # GB10 may report N/A for memory while utilization is valid.
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return info


def emit(event, *, path=None, echo=True, **data):
    record = {"event": event, "timestamp_utc": utc_now(),
              "job": os.environ.get("EMBER_JOB", "unknown"),
              "workflow_id": os.environ.get("EMBER_WORKFLOW_ID") or os.environ.get("FUZZBALL_WORKFLOW_ID"),
              "experiment_id": os.environ.get("EMBER_EXPERIMENT_ID"),
              **data}
    line = json.dumps(record, allow_nan=False, separators=(",", ":"), default=str)
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as out:
            out.write(line + "\n")
            out.flush()
    if echo:
        print(PREFIX + line, flush=True)
    return record
