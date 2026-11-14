"""Measured ForeFire CLI runner; it never fabricates engine results when unavailable."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import time

import psutil

from processing.feature_builder import write_json_atomic


def run_forefire(executable: str, script: str | Path, run_directory: str | Path, timeout_seconds: int = 3600) -> dict:
    script, run_directory = Path(script), Path(run_directory)
    run_directory.mkdir(parents=True, exist_ok=True)
    record = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "executable": executable, "script": str(script),
              "working_directory": str(run_directory), "measurement_method": "psutil RSS sampling every 0.1 seconds"}
    binary = shutil.which(executable)
    if binary is None:
        record.update({"status": "blocked", "reason": f"Executable not found on PATH: {executable}"})
        write_json_atomic(run_directory / "run_manifest.json", record)
        return record
    started = time.perf_counter()
    process = subprocess.Popen([binary, "-i", str(script)], cwd=run_directory, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tracked, peak_rss = psutil.Process(process.pid), 0
    try:
        while process.poll() is None:
            peak_rss = max(peak_rss, tracked.memory_info().rss)
            time.sleep(0.1)
        stdout, stderr = process.communicate(timeout=5)
        record.update({"status": "complete" if process.returncode == 0 else "failed", "return_code": process.returncode,
                       "wall_seconds": time.perf_counter() - started, "peak_rss_bytes": peak_rss, "stdout": stdout, "stderr": stderr})
    except subprocess.TimeoutExpired:
        process.kill()
        record.update({"status": "timed_out", "wall_seconds": time.perf_counter() - started, "peak_rss_bytes": peak_rss})
    write_json_atomic(run_directory / "run_manifest.json", record)
    return record
