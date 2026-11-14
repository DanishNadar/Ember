"""Extract and inspect a ForeFire arrival-time NetCDF reference artifact."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from processing.feature_builder import provenance, write_json_atomic


def extract_arrival_time(source: str | Path, output_root: str | Path, artifact_id: str, fill_value: float = -9999.0) -> dict:
    try:
        import h5py
    except ImportError as error:
        return {"status": "blocked", "reason": f"h5py is required: {error}"}
    source, output_root = Path(source), Path(output_root)
    raw_dir, processed_dir = output_root / "raw" / artifact_id, output_root / "processed" / artifact_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    copied = raw_dir / source.name
    if source.resolve() != copied.resolve():
        shutil.copy2(source, copied)
    try:
        with h5py.File(copied, "r") as handle:
            if "arrival_time_of_front" not in handle:
                raise ValueError("arrival_time_of_front dataset is absent")
            arrival = handle["arrival_time_of_front"][...]
            domain_attributes = {name: float(value[0]) for name, value in handle["domain"].attrs.items() if name in {"SWx", "SWy", "Lx", "Ly"}}
        valid = arrival != fill_value
        values = arrival[valid]
        if not values.size:
            raise ValueError("arrival-time output contains no non-sentinel cells")
        np.savez_compressed(processed_dir / "arrival_time.npz", arrival_time=arrival, valid_mask=valid)
        extent = [domain_attributes["SWx"], domain_attributes["SWx"] + domain_attributes["Lx"],
                  domain_attributes["SWy"], domain_attributes["SWy"] + domain_attributes["Ly"]]
        figure = output_root / "figures" / f"{artifact_id}_arrival_time.png"
        figure.parent.mkdir(parents=True, exist_ok=True)
        figure_values = np.ma.masked_where(~valid, arrival)
        fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), constrained_layout=True)
        image = axes[0].imshow(figure_values, origin="lower", extent=extent, cmap="inferno", interpolation="nearest")
        axes[0].set(title="Full model domain", xlabel="X (model coordinate units)", ylabel="Y (model coordinate units)")
        rows, columns = np.where(valid)
        pad, height, width = 20, arrival.shape[0], arrival.shape[1]
        row_start, row_end = max(0, rows.min() - pad), min(height, rows.max() + pad + 1)
        column_start, column_end = max(0, columns.min() - pad), min(width, columns.max() + pad + 1)
        zoom_extent = [extent[0] + column_start / width * domain_attributes["Lx"], extent[0] + column_end / width * domain_attributes["Lx"],
                       extent[2] + row_start / height * domain_attributes["Ly"], extent[2] + row_end / height * domain_attributes["Ly"]]
        axes[1].imshow(figure_values[row_start:row_end, column_start:column_end], origin="lower", extent=zoom_extent, cmap="inferno", interpolation="nearest")
        axes[1].set(title="Active-arrival region (20-cell padding)", xlabel="X (model coordinate units)", ylabel="Y (model coordinate units)")
        fig.colorbar(image, ax=axes, label="arrival time (seconds; inferred from fixture script)")
        fig.suptitle("ForeFire reference arrival-time artifact (not a local run)")
        fig.savefig(figure, dpi=160)
        plt.close(fig)
        record = {**provenance(copied, artifact_id, {"dataset": "arrival_time_of_front", "fill_value": fill_value}), "status": "complete",
                  "domain": domain_attributes, "arrival_time": {"shape": list(arrival.shape), "valid_cells": int(valid.sum()),
                    "total_cells": int(arrival.size), "min_seconds": float(values.min()), "max_seconds": float(values.max()),
                    "mean_seconds": float(values.mean()), "fill_cells": int((~valid).sum())},
                  "artifacts": {"arrival_npz": str(processed_dir / "arrival_time.npz"), "figure": str(figure)},
                  "caveat": "This is a checked-in reference output; Ember did not create it by running ForeFire locally."}
    except Exception as error:
        record = {**provenance(copied, artifact_id, {"dataset": "arrival_time_of_front", "fill_value": fill_value}), "status": "failed",
                  "error": f"{type(error).__name__}: {error}"}
    write_json_atomic(output_root / "arrival" / f"{artifact_id}.json", record)
    return record
