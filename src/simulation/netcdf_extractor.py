"""Read ForeFire HDF5-backed NetCDF landscapes when h5py is available.

The reader preserves native arrays and explicitly records its spatial mapping assumptions.
It does not treat NetCDF field names as guaranteed across ForeFire scenarios.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from processing.feature_builder import write_json_atomic


def _text(value: object) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def _domain_metadata(handle) -> dict:
    attrs = handle["domain"].attrs
    bbox = [float(item) for item in _text(attrs["BBoxWSEN"]).split(",")]
    return {"bbox_wsen": bbox, "SWx": float(attrs["SWx"][0]), "SWy": float(attrs["SWy"][0]),
            "Lx": float(attrs["Lx"][0]), "Ly": float(attrs["Ly"][0]), "native_crs": "not declared in this fixture"}


def inspect_landscape(path: str | Path) -> dict:
    try:
        import h5py
    except ImportError as error:
        return {"status": "reader-unavailable", "reason": str(error)}
    path = Path(path)
    with h5py.File(path, "r") as handle:
        layers = {}
        for name, value in handle.items():
            if not isinstance(value, h5py.Dataset) or "type" not in value.attrs:
                continue
            layers[name] = {"shape": list(value.shape), "dtype": str(value.dtype), "type": _text(value.attrs["type"]),
                            "fill_value": _text(value.attrs["_FillValue"]) if "_FillValue" in value.attrs else None}
        return {"status": "complete", "path": str(path), "netcdf_hdf5_properties": _text(handle.attrs.get("_NCProperties", "unknown")),
                "domain": _domain_metadata(handle), "layers": layers}


def _resample_native(layer: np.ndarray, source_bbox: list[float], target_bbox: list[float], target_shape: tuple[int, int]) -> np.ndarray:
    west, south, east, north = source_bbox
    xmin, ymin, xmax, ymax = target_bbox
    if not (west <= xmin <= xmax <= east and south <= ymin <= ymax <= north):
        raise ValueError("Target geometry extent lies outside landscape BBoxWSEN")
    rows, columns = layer.shape[-2:]
    xs = np.linspace(xmin, xmax, target_shape[1], endpoint=False) + (xmax - xmin) / (2 * target_shape[1])
    ys = np.linspace(ymin, ymax, target_shape[0], endpoint=False) + (ymax - ymin) / (2 * target_shape[0])
    column_index = np.clip(np.rint((xs - west) / (east - west) * (columns - 1)).astype(int), 0, columns - 1)
    row_index = np.clip(np.rint((ys - south) / (north - south) * (rows - 1)).astype(int), 0, rows - 1)
    return layer[..., row_index[:, None], column_index[None, :]]


def extract_environment(landscape: str | Path, manifest_path: str | Path) -> dict:
    """Align known fixture layers to a completed geometric-state raster.

    Uses the landscape's BBoxWSEN affine mapping. Row-axis orientation is retained
    as stored by the fixture and recorded as an assumption requiring engine-run validation.
    """
    try:
        import h5py
    except ImportError as error:
        return {"status": "blocked", "reason": f"h5py is required: {error}"}
    landscape, manifest_path = Path(landscape), Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        return {"status": "blocked", "reason": "State extraction is incomplete"}
    state = np.load(manifest["artifacts"]["state_npz"], allow_pickle=False)
    target_shape, target_bbox = tuple(state["burned_mask"].shape), state["bbox"].astype(float).tolist()
    output_path = Path(manifest["artifacts"]["state_npz"]).with_name("environment.npz")
    with h5py.File(landscape, "r") as handle:
        domain = _domain_metadata(handle)
        required = [name for name in ("fuel", "altitude", "wind") if name in handle]
        if not required:
            return {"status": "blocked", "reason": "No recognized fuel/altitude/wind layers found"}
        layers = {name: _resample_native(handle[name][...], domain["bbox_wsen"], target_bbox, target_shape) for name in required}
    np.savez_compressed(output_path, **layers)
    layer_stats = {}
    for name, values in layers.items():
        finite = values[np.isfinite(values)]
        layer_stats[name] = {"shape": list(values.shape), "dtype": str(values.dtype), "finite_count": int(finite.size),
                             "min": float(finite.min()) if finite.size else None, "max": float(finite.max()) if finite.size else None,
                             "mean": float(finite.mean()) if finite.size else None}
        if name == "fuel":
            unique, counts = np.unique(values, return_counts=True)
            layer_stats[name]["value_counts"] = {str(int(key)): int(count) for key, count in zip(unique, counts)}
    environment = {"status": "complete", "source_landscape": str(landscape), "output": str(output_path), "domain": domain,
                   "layers": layer_stats, "alignment": {"method": "nearest-neighbour sampling through BBoxWSEN", "target_bbox": target_bbox,
                     "row_axis_assumption": "native row order is south-to-north; validate against a ForeFire render before metric interpretation",
                     "temporal_alignment": "not established: source geometry has no timestamp and wind time index was retained"}}
    manifest["environment"] = environment
    write_json_atomic(manifest_path, manifest)
    return environment
