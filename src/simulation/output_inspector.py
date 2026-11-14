"""Inspect supported ForeFire artifacts without claiming their schemas are equivalent."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


class UnsupportedArtifact(ValueError):
    pass


def _kml_polygon_coordinates(path: Path) -> list[list[list[list[float]]]]:
    root = ET.parse(path).getroot()
    polygons: list[list[list[list[float]]]] = []
    for polygon in root.findall(".//{*}Polygon"):
        rings: list[list[list[float]]] = []
        for element in polygon.findall(".//{*}coordinates"):
            ring = []
            for token in (element.text or "").split():
                values = token.split(",")
                if len(values) >= 2:
                    ring.append([float(values[0]), float(values[1]), float(values[2]) if len(values) > 2 else 0.0])
            if ring:
                rings.append(ring)
        if rings:
            polygons.append(rings)
    return polygons


def inspect_artifact(path: str | Path) -> dict:
    path = Path(path)
    suffix = path.suffix.lower()
    result = {"path": str(path), "suffix": suffix, "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else None}
    if not path.exists():
        return {**result, "status": "missing"}
    if suffix in {".geojson", ".json"}:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            result.update({"status": "readable", "format": "geojson/json", "top_level_type": document.get("type"),
                           "feature_count": len(document.get("features", [])) if isinstance(document, dict) else None})
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            result.update({"status": "invalid", "error": str(error)})
    elif suffix == ".kml" or path.name.lower().endswith(".kml.ref"):
        try:
            polygons = _kml_polygon_coordinates(path)
            result.update({"status": "readable", "format": "kml", "polygon_count": len(polygons)})
        except (ET.ParseError, ValueError) as error:
            result.update({"status": "invalid", "error": str(error)})
    elif suffix == ".npz":
        with np.load(path, allow_pickle=False) as archive:
            result.update({"status": "readable", "format": "numpy-npz", "arrays": {name: list(archive[name].shape) for name in archive.files}})
    elif suffix == ".npy":
        result.update({"status": "readable", "format": "numpy-npy", "shape": list(np.load(path, mmap_mode="r").shape)})
    elif suffix == ".nc":
        reader = "netCDF4" if importlib.util.find_spec("netCDF4") else "xarray" if importlib.util.find_spec("xarray") else None
        result.update({"status": "reader-unavailable" if reader is None else "reader-available", "format": "netcdf",
                       "reader": reader, "note": "NetCDF metadata is intentionally not inferred without a reader."})
    else:
        result.update({"status": "unsupported", "format": None})
    return result


def load_polygons(path: str | Path) -> tuple[list[list[list[list[float]]]], dict]:
    """Load only polygon geometry, returning source metadata separately."""
    path = Path(path)
    if path.suffix.lower() == ".kml" or path.name.lower().endswith(".kml.ref"):
        return _kml_polygon_coordinates(path), {"format": "kml", "crs": "unspecified"}
    if path.suffix.lower() not in {".json", ".geojson"}:
        raise UnsupportedArtifact(f"Geometry extraction supports GeoJSON and KML, not {path.suffix}")
    document = json.loads(path.read_text(encoding="utf-8"))
    geometries = []
    if document.get("type") == "FeatureCollection":
        geometries = [feature.get("geometry") for feature in document.get("features", [])]
    elif document.get("type") == "Feature":
        geometries = [document.get("geometry")]
    else:
        geometries = [document]
    polygons = []
    for geometry in filter(None, geometries):
        if geometry.get("type") == "Polygon":
            polygons.append(geometry["coordinates"])
        elif geometry.get("type") == "MultiPolygon":
            polygons.extend(geometry["coordinates"])
    metadata = {"format": "geojson", "crs": document.get("crs", {}).get("properties", {}).get("name", "unspecified"),
                "valid_at": document.get("valid_at")}
    return polygons, metadata
