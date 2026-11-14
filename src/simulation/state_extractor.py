"""Convert a single ForeFire geometry artifact into Ember raw and processed state."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import numpy as np

from processing.feature_builder import provenance, validate_snapshot, write_json_atomic
from processing.geometry_processor import geometry_metrics
from processing.rasterizer import rasterize
from simulation.output_inspector import inspect_artifact, load_polygons


def extract_state(source: str | Path, output_root: str | Path, scenario_id: str, grid_shape: tuple[int, int] = (256, 256), resume: bool = False) -> dict:
    source, output_root = Path(source), Path(output_root)
    manifest_path = output_root / "manifests" / f"{scenario_id}.json"
    if resume and manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return {**existing, "resumed": True}
    raw_dir, processed_dir = output_root / "raw" / scenario_id, output_root / "processed" / scenario_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    copied_source = raw_dir / source.name
    if source.resolve() != copied_source.resolve():
        shutil.copy2(source, copied_source)
    inspection = inspect_artifact(copied_source)
    try:
        polygons, source_metadata = load_polygons(copied_source)
        mask, grid = rasterize(polygons, grid_shape)
        metrics = geometry_metrics(polygons)
        validation = validate_snapshot(mask, int(metrics["polygon_count"]))
        feature_collection = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"scenario_id": scenario_id}, "geometry": {"type": "Polygon", "coordinates": polygon}}
            for polygon in polygons]}
        (processed_dir / "front.geojson").write_text(json.dumps(feature_collection, indent=2), encoding="utf-8")
        np.savez_compressed(processed_dir / "state.npz", burned_mask=mask, bbox=np.asarray(grid["bbox"], dtype=float))
        status = "complete" if validation["valid"] else "invalid"
        manifest = {**provenance(copied_source, scenario_id, {"grid_shape": list(grid_shape)}), "status": status,
                    "inspection": inspection, "source_metadata": source_metadata, "geometry_metrics": metrics,
                    "grid": grid, "validation": validation,
                    "artifacts": {"raw_source": str(copied_source), "front_geojson": str(processed_dir / "front.geojson"),
                                  "state_npz": str(processed_dir / "state.npz")}}
    except Exception as error:  # Persist failures so batch work is resume-safe.
        manifest = {**provenance(copied_source, scenario_id, {"grid_shape": list(grid_shape)}), "status": "failed",
                    "inspection": inspection, "error": f"{type(error).__name__}: {error}"}
    write_json_atomic(manifest_path, manifest)
    return manifest
