"""Provenance, atomic manifests, and scenario-level dataset utilities."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import tempfile
from typing import Any

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(payload, temporary, indent=2, sort_keys=True)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def provenance(source: Path, scenario_id: str, configuration: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "scenario_id": scenario_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"path": str(source), "sha256": sha256(source), "size_bytes": source.stat().st_size},
        "configuration": configuration,
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__},
    }


def validate_snapshot(mask: np.ndarray, polygon_count: int) -> dict[str, Any]:
    problems = []
    if mask.ndim != 2:
        problems.append("mask is not two-dimensional")
    if polygon_count == 0:
        problems.append("no polygon geometry was extracted")
    if not np.isin(mask, [0, 1]).all():
        problems.append("mask is not binary")
    return {"valid": not problems, "problems": problems, "burned_cells": int(mask.sum()), "total_cells": int(mask.size)}
