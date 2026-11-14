"""Structured, append-only observability for real Ember jobs.

The JSON line and stdout marker carry the same event. No synthetic measurements
are inserted when a metric or device is unavailable.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
from datetime import datetime, timezone


PREFIX = "EMBER_EVENT "


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def resources():
    """A point-in-time snapshot, NOT average CPU/GPU utilization."""
    info = {"host": socket.gethostname(), "pid": os.getpid(),
            "cpu_allocated": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()}
    try:
        import psutil
        proc = psutil.Process()
        info.update(process_rss_mb=round(proc.memory_info().rss / 1048576, 2),
                    host_cpu_percent_snapshot=psutil.cpu_percent(interval=None),
                    host_memory_percent_snapshot=psutil.virtual_memory().percent)
    except (ImportError, OSError):
        pass
    try:
        p = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3)
        if p.returncode == 0 and p.stdout.strip():
            vals = [v.strip() for v in p.stdout.splitlines()[0].split(",")]
            info.update(gpu_utilization_percent_snapshot=float(vals[0]),
                        gpu_memory_used_mib_snapshot=float(vals[1]),
                        gpu_memory_total_mib=float(vals[2]))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return info


def emit(event, *, path=None, echo=True, **data):
    record = {"event": event, "timestamp_utc": utc_now(),
              "job": os.environ.get("EMBER_JOB", "unknown"),
              "workflow_id": os.environ.get("EMBER_WORKFLOW_ID"),
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
