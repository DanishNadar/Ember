"""Generate measured spatial/data-quality summaries from processed Ember states."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from processing.feature_builder import write_json_atomic


def analyze_scenario(manifest_path: str | Path, output_root: str | Path) -> dict:
    manifest_path, output_root = Path(manifest_path), Path(output_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        result = {"scenario_id": manifest.get("scenario_id"), "status": "blocked", "reason": "Extraction did not complete", "source_manifest": str(manifest_path)}
        write_json_atomic(output_root / "analysis" / f"{manifest.get('scenario_id', 'unknown')}.json", result)
        return result
    state = np.load(manifest["artifacts"]["state_npz"], allow_pickle=False)
    mask, bbox = state["burned_mask"], state["bbox"]
    metrics = manifest["geometry_metrics"]
    burned_fraction = float(mask.mean())
    environment = manifest.get("environment")
    environment_quality = "not available: no aligned environmental rasters were extracted"
    environmental = None
    if environment and environment.get("status") == "complete":
        environment_quality = "available with recorded spatial/temporal alignment caveats; no causal inference is made"
        environmental = {"layers": environment["layers"], "alignment": environment["alignment"]}
    result = {
        "scenario_id": manifest["scenario_id"], "status": "complete", "source_manifest": str(manifest_path),
        "data_quality": {"missing_values": int(np.isnan(mask).sum()), "empty_state": bool(mask.sum() == 0),
                         "class_imbalance_burned_fraction": burned_fraction, "temporal_analysis": "not available: one extracted state",
                         "environmental_analysis": environment_quality},
        "spatial": {**metrics, "raster_shape": list(mask.shape), "raster_burned_fraction": burned_fraction,
                    "area_units": "source coordinate units squared; do not interpret as square metres without a projected CRS"},
        "computational": {"engine_runtime": "not measured: supplied reference artifact was analyzed without an engine run",
                           "extraction_runtime": "not captured in this first reference-artifact analysis"},
    }
    if environmental:
        result["environmental"] = environmental
    figure_dir = output_root / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    figure_path = figure_dir / f"{manifest['scenario_id']}_front_and_mask.png"
    fig, (front_ax, mask_ax) = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    front = json.loads(Path(manifest["artifacts"]["front_geojson"]).read_text(encoding="utf-8"))
    for feature in front["features"]:
        for ring in feature["geometry"]["coordinates"]:
            array = np.asarray(ring)
            front_ax.plot(array[:, 0], array[:, 1], linewidth=0.7)
    front_ax.set(title="Extracted fire-front geometry", xlabel="X (source coordinate units)", ylabel="Y (source coordinate units)")
    plot_extent = [bbox[0], bbox[2], bbox[1], bbox[3]]  # matplotlib order: left, right, bottom, top
    mask_ax.imshow(mask, origin="lower", extent=plot_extent, cmap="YlOrRd", interpolation="nearest")
    mask_ax.set(title="Rasterized burned mask", xlabel="X (source coordinate units)", ylabel="Y (source coordinate units)")
    fig.suptitle(f"Ember reference-artifact analysis: {manifest['scenario_id']} (not a local ForeFire run)")
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)
    artifacts = {"front_and_mask_figure": str(figure_path)}
    if environment and environment.get("status") == "complete":
        values = np.load(environment["output"], allow_pickle=False)
        environmental_figure = figure_dir / f"{manifest['scenario_id']}_environment.png"
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), constrained_layout=True)
        fuel, altitude, wind = values["fuel"][0, 0], values["altitude"][0, 0], values["wind"]
        for axis, image, title, label in (
            (axes[0], fuel, "Fuel index", "index"),
            (axes[1], altitude, "Altitude", "native value"),
            (axes[2], wind[0, 0], "Wind slice [0, 0]", "native value"),
        ):
            view = axis.imshow(image, origin="lower", extent=plot_extent, interpolation="nearest")
            axis.set(title=title, xlabel="Longitude (degrees)", ylabel="Latitude (degrees)")
            fig.colorbar(view, ax=axis, label=label)
        fig.suptitle("Ember aligned landscape fields (nearest-neighbour; see manifest assumptions)")
        fig.savefig(environmental_figure, dpi=160)
        plt.close(fig)
        artifacts["environment_figure"] = str(environmental_figure)
    result["artifacts"] = artifacts
    write_json_atomic(output_root / "analysis" / f"{manifest['scenario_id']}.json", result)
    return result
